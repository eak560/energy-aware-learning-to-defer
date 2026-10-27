"""Models behind the laptop demo, reusing the project's own code so the demo computes what the paper measured.

  device  256 KB int8 hashed n-gram model (outputs/models/ngram256KB_v2.npz), as on the ESP32-S3
  router  deferral model for the RoBERTa-base hub (outputs/models/defer_router_roberta_base_1m.npz)
  hub     RoBERTa-base trained with 1M extra reviews (outputs/models/roberta_base_1m_best), as on the Pi Zero 2 W
  energy  the paper's device energy model (src/energy_curves.py): datasheet currents, placeholder timings

Routing thresholds are chosen on the 5,000 validation reviews, as in the paper: for a send budget of r, the
threshold is the (1 - r) quantile of the router's validation scores.

    .venv/bin/python -I demo/engine.py      # self-check against the paper's saved numbers
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from sklearn.feature_extraction.text import HashingVectorizer  # noqa: E402
from sklearn.utils import murmurhash3_32  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402

from chip_model import MAX_BITS, _hash_chunk, binary_csr, device_proba  # noqa: E402
from common import MODELS_DIR, clean_text, load_proba, load_split  # noqa: E402
from defer_router import DEFER_BITS, load_cached, router_features  # noqa: E402
from energy_curves import BATTERY_J, PARAMS  # noqa: E402
from train_hub import pad_batch, tokenize  # noqa: E402
from train_transformer import pick_device  # noqa: E402

HUB_DIR = MODELS_DIR / "roberta_base_1m_best"
ESP32_SRAM = 512 * 1024
P = {k: v["value"] for k, v in PARAMS.items()}


class Device:
    """The on-chip model: hash word 1-2-grams, add the buckets' int8 weights / sqrt(n), sigmoid."""

    def __init__(self):
        z = np.load(MODELS_DIR / "ngram256KB_v2.npz")
        self.q, self.scale, self.bias, self.bits = z["weights"], float(z["scale"]), float(z["bias"]), int(z["bits"])
        self.analyzer = HashingVectorizer(ngram_range=(1, 2)).build_analyzer()  # same tokens as _hash_chunk
        self.bytes = int(self.q.nbytes)

    def hash(self, texts):
        indices, row_nnz = _hash_chunk(texts)
        return binary_csr(indices, row_nnz=row_nnz)

    def proba(self, B):
        return device_proba(B, self.bits, (self.q, self.scale, self.bias))

    def bucket(self, gram):
        # HashingVectorizer: index = |murmurhash3_32(token, seed=0)| mod 2^20; the chip keeps the low 18 bits
        return (abs(murmurhash3_32(gram, seed=0)) % 2 ** MAX_BITS) & (2 ** self.bits - 1)

    def explain(self, text, k=5):
        """The n-grams that pushed the score most, with each bucket's share of the sum."""
        buckets = {}
        for gram in dict.fromkeys(self.analyzer(text)):
            buckets.setdefault(self.bucket(gram), []).append(gram)
        if not buckets:
            return [], [], 0
        norm = 1 / np.sqrt(len(buckets))
        items = sorted(((float(self.q[b]) * self.scale * norm, grams) for b, grams in buckets.items()),
                       key=lambda t: t[0])
        fmt = lambda c, grams: {"text": " / ".join(grams[:2]), "weight": round(c, 3)}
        pos = [fmt(c, g) for c, g in reversed(items) if c > 0][:k]
        neg = [fmt(c, g) for c, g in items if c < 0][:k]
        return pos, neg, len(buckets)


class Router:
    """Deferral model: 3-class logistic regression on 2^16 hashed n-grams + confidence and length bins."""

    def __init__(self):
        z = np.load(MODELS_DIR / "defer_router_roberta_base_1m.npz")
        self.coef, self.intercept, self.classes = z["coef"], z["intercept"], list(z["classes"])
        # On the device only two weight tables are needed: logits relative to "no change" (class 0).
        self.bytes = 2 * 2 ** DEFER_BITS + 2 * (self.coef.shape[1] - 2 ** DEFER_BITS)

    def score(self, B, p_device):
        logits = router_features(B, p_device) @ self.coef.T + self.intercept
        logits = np.asarray(logits) - np.max(logits, axis=1, keepdims=True)
        prob = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
        return prob[:, self.classes.index(1)] - prob[:, self.classes.index(-1)]


class Hub:
    def __init__(self):
        self.device = pick_device("auto")
        self.tokenizer = AutoTokenizer.from_pretrained(HUB_DIR)
        self.model = AutoModelForSequenceClassification.from_pretrained(HUB_DIR, dtype=torch.float32).to(self.device).eval()
        self.params = sum(p.numel() for p in self.model.parameters())
        self.bytes_fp32 = (HUB_DIR / "model.safetensors").stat().st_size

    @torch.no_grad()
    def proba(self, texts, batch_size=16):
        tok = tokenize(self.tokenizer, list(texts), 512, 128)  # first 128 + last 382 tokens, as in training
        order = np.argsort(tok.lengths())
        out = np.empty(len(tok), dtype=np.float32)
        for s in range(0, len(order), batch_size):
            rows = order[s:s + batch_size]
            ids, mask = pad_batch(tok, rows, self.tokenizer.pad_token_id)
            logits = self.model(input_ids=ids.to(self.device), attention_mask=mask.to(self.device)).logits
            out[rows] = torch.softmax(logits.float(), -1)[:, 1].cpu().numpy()
        return out


def energy(sent: bool):
    """Device energy for one review, in mJ, split into the parts the paper's model adds up."""
    compute = P["V"] * P["I_cpu"] * P["t_local"] * 1000
    tx = P["V"] * P["I_tx"] * P["t_tx"] * 1000 if sent else 0.0
    rx = P["V"] * P["I_rx"] * P["t_wait"] * 1000 if sent else 0.0
    return {"compute": compute, "tx": tx, "rx": rx, "total": compute + tx + rx}


class Engine:
    POLICIES = ("confidence", "learned")

    def __init__(self):
        t0 = time.perf_counter()
        self.device, self.router, self.hub = Device(), Router(), Hub()
        B_val, _ = load_cached("val")
        p_val = self.device.proba(B_val)
        self.val_scores = {"confidence": 1 - np.maximum(p_val, 1 - p_val), "learned": self.router.score(B_val, p_val)}
        test = load_split("test")
        self.test_text, self.test_y = test["text"].tolist(), test["label"].to_numpy()
        self.test_hub = load_proba("roberta_base_1m", "test")  # saved predictions of this same hub
        self.samples = self._pick_samples()
        self.load_seconds = time.perf_counter() - t0

    def threshold(self, policy, rate):
        if rate <= 0:
            return np.inf
        if rate >= 1:
            return -np.inf
        return float(np.quantile(self.val_scores[policy], 1 - rate))

    def _route(self, B, p, policy, rate):
        score = 1 - np.maximum(p, 1 - p) if policy == "confidence" else self.router.score(B, p)
        return score, score > self.threshold(policy, rate)

    def classify(self, text, policy="confidence", rate=0.16):
        text = clean_text(text.strip())
        t0 = time.perf_counter()
        B = self.device.hash([text])
        p = float(self.device.proba(B)[0])
        score, sent = self._route(B, np.array([p]), policy, rate)
        device_ms = (time.perf_counter() - t0) * 1000
        pos, neg, n = self.device.explain(text)
        out = {
            "device": {"label": int(p >= 0.5), "p_pos": p, "confidence": max(p, 1 - p), "top_pos": pos,
                       "top_neg": neg, "buckets": n, "laptop_ms": device_ms},
            "route": {"policy": policy, "rate": rate, "score": float(score[0]),
                      "threshold": self.threshold(policy, rate), "sent": bool(sent[0])},
            "energy": energy(bool(sent[0])),
            "bytes_sent": len(text.encode("utf-8")) if sent[0] else 0,
        }
        if sent[0]:
            t0 = time.perf_counter()
            ph = float(self.hub.proba([text])[0])
            out["hub"] = {"label": int(ph >= 0.5), "p_pos": ph, "laptop_ms": (time.perf_counter() - t0) * 1000}
        out["final"] = out["hub"]["label"] if sent[0] else out["device"]["label"]
        return out

    def batch(self, n=100, policy="confidence", rate=0.16, seed=0):
        """Run n random official test reviews through the whole system; the hub runs live on the sent ones."""
        idx = np.random.default_rng(seed).choice(len(self.test_y), n, replace=False)
        texts, y = [self.test_text[i] for i in idx], self.test_y[idx]
        B = self.device.hash(texts)
        p = self.device.proba(B)
        _, sent = self._route(B, p, policy, rate)
        pred = (p >= 0.5).astype(int)
        t0 = time.perf_counter()
        if sent.any():
            pred[sent] = (self.hub.proba([t for t, s in zip(texts, sent) if s]) >= 0.5).astype(int)
        hub_s = time.perf_counter() - t0
        e = sum(energy(bool(s))["total"] for s in sent)
        return {"n": n, "sent": int(sent.sum()), "accuracy": float((pred == y).mean()),
                "device_accuracy": float(((p >= 0.5) == y).mean()),
                "hub_accuracy": float(((self.test_hub[idx] >= 0.5) == y).mean()),
                "energy_mJ": e, "send_all_mJ": n * energy(True)["total"], "device_only_mJ": n * energy(False)["total"],
                "hub_laptop_s": hub_s}

    def _pick_samples(self):
        """Short official test reviews that show each case, picked from the saved predictions."""
        words = np.array([len(t.split()) for t in self.test_text])
        p = load_proba("ngram256KB", "test")
        conf, dev_ok, hub_ok = np.maximum(p, 1 - p), (p >= 0.5) == self.test_y, (self.test_hub >= 0.5) == self.test_y
        short = (words >= 25) & (words <= 70)
        cases = [
            ("Clearly positive", short & dev_ok & (conf > 0.97) & (self.test_y == 1)),
            ("Clearly negative", short & dev_ok & (conf > 0.97) & (self.test_y == 0)),
            ("Device unsure, hub fixes it", short & ~dev_ok & hub_ok & (conf < 0.62)),
            ("Device unsure but right", short & dev_ok & hub_ok & (conf < 0.62)),
        ]
        rng = np.random.default_rng(7)
        out = [{"name": name, "text": self.test_text[rng.choice(np.flatnonzero(mask))]} for name, mask in cases]
        out += [
            {"name": "Mixed (written for the demo)", "text": "The plot was predictable and the first hour drags, "
             "but the two leads are so good together that I ended up enjoying it more than I expected."},
            {"name": "Sarcastic (written for the demo)", "text": "Oh great, another two hours of my life I will "
             "never get back. Truly a masterpiece of boredom."},
        ]
        return out

    def info(self):
        return {
            "device_bytes": self.device.bytes, "device_weights": int(self.device.q.size),
            "router_bytes": self.router.bytes, "sram_bytes": ESP32_SRAM,
            "hub_params": int(self.hub.params), "hub_bytes_fp32": int(self.hub.bytes_fp32),
            "hub_bytes_int8": int(self.hub.params), "hub_device": str(self.hub.device),
            "energy_params": PARAMS, "battery_J": BATTERY_J,
            "energy_local": energy(False), "energy_sent": energy(True),
            "samples": self.samples, "load_seconds": self.load_seconds,
        }


def self_check():
    """Confirm the demo reproduces the paper's saved predictions and an operating point."""
    eng = Engine()
    print(f"loaded in {eng.load_seconds:.1f}s on {eng.hub.device}")
    B_test, y = load_cached("test")
    p = eng.device.proba(B_test)
    print("device matches saved predictions:", np.allclose(p, load_proba("ngram256KB", "test"), atol=1e-5))
    hv = HashingVectorizer(n_features=2 ** MAX_BITS, ngram_range=(1, 2), alternate_sign=False, binary=True, norm=None)
    text = eng.test_text[0]
    ours = sorted({eng.device.bucket(g) for g in eng.device.analyzer(text)})
    theirs = sorted(set((hv.transform([text]).indices & (2 ** eng.device.bits - 1)).tolist()))
    print("n-gram buckets match the vectorizer:", ours == theirs)
    for policy, expect in [("confidence", 0.95136), ("learned", 0.95228)]:
        score, sent = eng._route(B_test, p, policy, 0.10)
        acc = np.where(sent, eng.test_hub >= 0.5, p >= 0.5) == y
        print(f"{policy} at 10%: sends {sent.mean():.2%}, accuracy {acc.mean():.5f} (paper {expect})")
    live = eng.hub.proba(eng.test_text[:48])
    print("hub matches saved predictions on 48 reviews:", float(np.abs(live - eng.test_hub[:48]).max()) < 0.02)
    print(eng.classify("A wonderful, moving film with brilliant acting.")["final"],
          eng.classify(eng.samples[2]["text"])["route"]["sent"])


if __name__ == "__main__":
    self_check()
