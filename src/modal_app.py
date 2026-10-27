"""Run the hub trainer (src/train_hub.py) on Modal cloud GPUs.

One-time sign-in (run it yourself; it opens your browser and saves ~/.modal.toml):
    .venv/bin/python -m modal setup

Upload the data once (~1.2 GB: official splits + the clean v2 pool slices):
    .venv/bin/python -m modal run src/modal_app.py::upload

Cache tokens on a cheap CPU machine (no GPU billing), then train on a GPU:
    .venv/bin/python -m modal run src/modal_app.py::tokenize --model roberta-large --pool-reviews 1000000
    .venv/bin/python -m modal run --detach src/modal_app.py::train --gpu H100 --max-hours 3 \
        --args "--model roberta-large --pool-reviews 1000000 --prefix roberta_large_1m --lr 1e-5 --batch-size 32 --accum 1 --skip-defer"

--max-hours is a hard cost cap per run (H100 = $3.95/h). The account budget is $30.

Training checkpoints to the volume and resumes if rerun with the same --prefix.
Fetch results (prediction .npy files and metrics .json, a few MB):
    .venv/bin/python -m modal volume get ai-sentiment outputs ./outputs_modal
"""

import os
import shlex
import subprocess
import threading
from pathlib import Path

import modal

LOCAL = Path(__file__).resolve().parent.parent
PROJECT = "/root/project"
VOL_PATH = "/vol"

app = modal.App("ai-sentiment-hub")
volume = modal.Volume.from_name("ai-sentiment", create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.14.1", "transformers==5.20.1", "pyarrow==26.0.0", "numpy==2.5.4", "pandas==3.0.6",
                 "scikit-learn==1.9.1", "scipy==1.18.1", "tqdm", "sentencepiece", "protobuf")
    .env({"HF_HOME": f"{VOL_PATH}/hf_cache", "TOKENIZERS_PARALLELISM": "true"})
    .add_local_dir(LOCAL / "src", f"{PROJECT}/src", ignore=["__pycache__", "._*", "modal_app.py"])
)


def _link_volume():
    """Make /root/project/{data,outputs} point at the persistent volume, as the scripts expect."""
    for name in ("data", "outputs"):
        target = Path(VOL_PATH) / name
        target.mkdir(parents=True, exist_ok=True)
        link = Path(PROJECT) / name
        if not link.exists():
            link.symlink_to(target)


def _run(args: list[str], script: str = "src/train_hub.py"):
    _link_volume()
    stop = threading.Event()

    def commit_regularly():  # persist checkpoints even if the container is pre-empted
        while not stop.wait(600):
            volume.commit()

    threading.Thread(target=commit_regularly, daemon=True).start()
    try:
        subprocess.run(["python", "-I", script, *args], cwd=PROJECT, check=True)
    finally:
        stop.set()
        volume.commit()


@app.function(image=image, volumes={VOL_PATH: volume}, cpu=8, memory=32768, timeout=6 * 3600)
def tokenize_remote(args: list[str]):
    _run([*args, "--tokenize-only"])


@app.function(image=image, volumes={VOL_PATH: volume}, gpu="H100", cpu=4, memory=32768, timeout=3600, retries=0)
def train_remote(args: list[str]):
    import torch
    print("GPU:", torch.cuda.get_device_name(0), flush=True)
    _run(args)


@app.function(image=image, volumes={VOL_PATH: volume}, gpu="H100", cpu=4, memory=32768, timeout=1800, retries=0)
def predict_remote(args: list[str]):
    _run(args, script="src/predict_hub.py")


@app.local_entrypoint()
def upload():
    files = [*(LOCAL / "data" / "splits").glob("[!._]*.parquet"),
             *[LOCAL / "data" / "pool" / "splits_v2" / f"{n}.parquet" for n in ("chip_train", "defer", "val_pool")]]
    with volume.batch_upload(force=True) as batch:
        for f in files:
            remote = "/data/" + str(f.relative_to(LOCAL / "data"))
            batch.put_file(str(f), remote)
            print(f"queued {f.stat().st_size / 1e6:7.1f} MB  {remote}")
    print("upload finished")


@app.local_entrypoint()
def tokenize(model: str = "roberta-large", pool_reviews: int = 1_000_000, max_len: int = 512, head: int = 128):
    tokenize_remote.remote(["--model", model, "--pool-reviews", str(pool_reviews), "--prefix", "tokenize_only",
                            "--max-len", str(max_len), "--head", str(head)])


@app.local_entrypoint()
def train(args: str, gpu: str = "H100", max_hours: float = 1.0):
    """max_hours is a hard stop for this run's cost: the container is killed at the limit.
    Rerunning with the same --prefix resumes from the last checkpoint."""
    rate = {"H100": 3.95, "A100-80GB": 2.50, "A100-40GB": 2.10, "L40S": 1.95}.get(gpu)
    if rate:
        print(f"{gpu}: at most {max_hours:.2f} h, about ${rate * max_hours:.2f} of GPU time")
    fn = train_remote.with_options(gpu=gpu, timeout=int(max_hours * 3600))
    fn.remote(shlex.split(args))


@app.local_entrypoint()
def predict(prefix: str, gpu: str = "H100", max_hours: float = 0.5):
    """Long-review (sliding-window) predictions for a trained hub; hard time cap as for train."""
    predict_remote.with_options(gpu=gpu, timeout=int(max_hours * 3600)).remote(["--prefix", prefix])
