"""Live dashboard for the project's background jobs.

Reads the job logs in outputs/logs/ every few seconds and shows each job in
plain language with a progress bar, time left and accuracy so far, plus the
Modal spend against the $30 budget. Standard library only.

    .venv/bin/python -I src/dashboard.py        # then open http://localhost:8765
"""

import json
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "outputs" / "logs"
PYTHON = ROOT / ".venv" / "bin" / "python"
BUDGET = 30.0
PORT = 8765

TASKS = [
    {"id": "baseline", "kind": "train", "log": "modal_rl_official.log", "title": "Baseline model",
     "what": "RoBERTa-large on the original 20,000 reviews only. Reproduces the published score to prove the setup is sound."},
    {"id": "roberta", "kind": "train", "log": "modal_rl_1m.log", "title": "RoBERTa-large + 1M extra reviews",
     "what": "A large model learning from 1 million extra cleaned movie reviews."},
    {"id": "electra", "kind": "train", "log": "modal_electra_1m.log", "title": "ELECTRA-large + 1M extra reviews",
     "what": "A differently trained large model, so the team of models makes different mistakes."},
    {"id": "deberta", "kind": "train", "log": "modal_deberta_1m.log", "title": "DeBERTa-v3-large + 1M extra reviews",
     "what": "The third large model, adding more variety to the team."},
    {"id": "ngram", "kind": "parts", "log": "ngram_v2.log", "parts": ["ngram1024KB", "ngram256KB"],
     "title": "Small on-chip model (retrained)",
     "what": "The tiny word-pattern model, retrained on the cleaned data. Runs on your Mac."},
    {"id": "pred_roberta", "kind": "predict", "log": "modal_pred_rl.log", "title": "Long reviews: RoBERTa",
     "what": "Re-reads long reviews in overlapping pieces instead of cutting them short."},
    {"id": "pred_electra", "kind": "predict", "log": "modal_pred_electra.log", "title": "Long reviews: ELECTRA",
     "what": "Same full re-read of long reviews, for ELECTRA."},
    {"id": "pred_deberta", "kind": "predict", "log": "modal_pred_deberta.log", "title": "Long reviews: DeBERTa",
     "what": "Same full re-read of long reviews, for DeBERTa. Starts after DeBERTa finishes."},
    {"id": "ensemble", "kind": "result", "file": "outputs/ensemble_results.json", "title": "Final team + one test score",
     "what": "Combines the models (chosen on the 50k practice set), then scores the test set exactly once."},
]

STEP = re.compile(r"^step ([\d,]+)/([\d,]+)\s+loss (\S+)\s+([\d.]+) reviews/s")
VALPOOL = re.compile(r"val_pool accuracy ([\d.]+) at step ([\d,]+)")
PRED = re.compile(r"^(val|val_pool|test) \{'accuracy': ([\d.]+)")
STALE_SECONDS = 15 * 60
BATCH = 32

spend = {"metered": None, "checked": None}


def lines_of(path: Path):
    return [l.strip() for l in re.split(r"[\r\n]+", path.read_text(errors="replace")) if l.strip()]


def base(task, state, progress=0.0, **extra):
    return {"id": task["id"], "title": task["title"], "what": task["what"], "state": state,
            "progress": round(progress, 4), **extra}


def train_status(task):
    path = LOGS / task["log"]
    if not path.exists():
        return base(task, "waiting")
    lines = lines_of(path)
    steps = [m for l in lines if (m := STEP.match(l))]
    vals = [m for l in lines if (m := VALPOOL.search(l))]
    final = next((json.loads(l) for l in lines if l.startswith('{"best_val"')), None)
    extra = {"val_pool": float(vals[-1].group(1)) if vals else None}
    if final:
        return base(task, "done", 1.0, val_pool=final["val_pool"]["accuracy"], test=final["test"]["accuracy"])
    if any("RemoteError" in l or l.startswith("Traceback") for l in lines):
        return base(task, "failed", **extra)
    if not steps:
        return base(task, "starting", 0.0, **extra)
    step, total = (int(x.replace(",", "")) for x in steps[-1].group(1, 2))
    speed = sum(float(m.group(4)) for m in steps[-5:]) / len(steps[-5:])
    eta = (total - step) * BATCH / speed if speed else None
    state = "stalled" if time.time() - path.stat().st_mtime > STALE_SECONDS else "running"
    note = "Finishing: final predictions" if step >= total else None
    return base(task, state, step / total, eta_seconds=eta, speed=round(speed), note=note,
                step=step, total=total, **extra)


def predict_status(task):
    path = LOGS / task["log"]
    if not path.exists():
        return base(task, "waiting")
    found = {m.group(1): float(m.group(2)) for l in lines_of(path) if (m := PRED.match(l))}
    if "test" in found:
        return base(task, "done", 1.0, val_pool=found.get("val_pool"), test=found["test"])
    if any("RemoteError" in l for l in lines_of(path)):
        return base(task, "failed")
    return base(task, "running", len(found) / 3, val_pool=found.get("val_pool"))


def parts_status(task):
    path = LOGS / task["log"]
    if not path.exists():
        return base(task, "waiting")
    lines = lines_of(path)
    done = [p for p in task["parts"] if any(l.startswith(p + " {") for l in lines)]
    if len(done) == len(task["parts"]):
        m = re.search(r"'val_pool': \{'accuracy': ([\d.]+)", next(l for l in lines if l.startswith(task["parts"][0])))
        t = re.search(r"'test': \{'accuracy': ([\d.]+)", next(l for l in lines if l.startswith(task["parts"][0])))
        return base(task, "done", 1.0, val_pool=float(m.group(1)) if m else None, test=float(t.group(1)) if t else None)
    return base(task, "running", len(done) / len(task["parts"]))


def result_status(task):
    path = ROOT / task["file"]
    if not path.exists():
        return base(task, "waiting")
    r = json.loads(path.read_text())
    return base(task, "done", 1.0, val_pool=r["chosen_on_val_pool"]["val_pool_cv"], test=r["test_accuracy"])


def status():
    handlers = {"train": train_status, "predict": predict_status, "parts": parts_status, "result": result_status}
    tasks = []
    for t in TASKS:
        try:
            tasks.append(handlers[t["kind"]](t))
        except Exception as e:  # a half-written log line should not break the page
            tasks.append(base(t, "unknown", note=str(e)[:80]))
    return {"tasks": tasks, "spend": spend, "budget": BUDGET, "updated": time.strftime("%H:%M:%S")}


def refresh_spend():
    while True:
        try:
            out = subprocess.run([str(PYTHON), "-m", "modal", "billing", "summary"], capture_output=True,
                                 text=True, timeout=60, cwd=ROOT).stdout
            m = re.search(r"Metered Cost:\s+([\d.]+)", out)
            if m:
                spend.update(metered=float(m.group(1)), checked=time.strftime("%H:%M"))
        except Exception:  # noqa: BLE001 - keep the last known value
            pass
        time.sleep(180)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Background Jobs</title>
<style>
:root{color-scheme:light;--surface:#fcfcfb;--card:#ffffff;--border:#e4e3df;--track:#f0efec;
--ink:#0b0b0b;--ink2:#52514e;--fill:#2a78d6}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--surface:#1a1a19;--card:#222220;--border:#383835;
--track:#383835;--ink:#ffffff;--ink2:#c3c2b7;--fill:#3987e5}}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:760px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--ink2);font-size:13px;margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;margin:0 0 10px}
.row{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.title{font-weight:600}
.chip{font-size:12px;color:var(--ink2);white-space:nowrap}
.what{color:var(--ink2);font-size:13px;margin:4px 0 10px}
.bar{height:8px;border-radius:4px;background:var(--track);overflow:hidden}
.bar>span{display:block;height:100%;background:var(--fill);border-radius:4px;transition:width .6s ease}
.meta{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:12px;color:var(--ink2);margin-top:8px;font-variant-numeric:tabular-nums}
.meta b{color:var(--ink);font-weight:600}
.budget .title{margin-bottom:8px}
.waiting{opacity:.62}
@media (prefers-reduced-motion:reduce){.bar>span{transition:none}}
</style></head>
<body><main>
<h1>Background jobs</h1>
<p class="sub" id="updated">Loading…</p>
<div id="budget"></div>
<div id="tasks"></div>
</main>
<script>
const ICON={done:"✓ Done",running:"● Running",starting:"◌ Starting",waiting:"○ Waiting",failed:"✕ Failed",stalled:"◐ No update for 15 min",unknown:"? Unknown"};
const pct=x=>x==null?"–":(x*100).toFixed(2)+"%";
const eta=s=>{if(s==null)return null;const m=Math.round(s/60);return m<60?m+" min left":Math.floor(m/60)+" h "+(m%60)+" min left"};
// Cards are built once and then updated in place, so nothing flickers or jumps while you read.
function ensureCard(id, parent){
  let el=document.getElementById("card-"+id);
  if(!el){el=document.createElement("div");el.id="card-"+id;el.className="card";
    el.innerHTML=`<div class="row"><span class="title"></span><span class="chip"></span></div><div class="what"></div>
    <div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="100"><span style="width:0%"></span></div><div class="meta"></div>`;
    parent.appendChild(el);}
  return el;
}
function fill(el, title, chip, what, p, meta){
  el.querySelector(".title").textContent=title;
  el.querySelector(".chip").textContent=chip;
  el.querySelector(".what").textContent=what;
  el.querySelector(".what").hidden=!what;
  const bar=el.querySelector(".bar");
  bar.setAttribute("aria-label",title); bar.setAttribute("aria-valuenow",Math.round(p*100));
  bar.firstElementChild.style.width=(p*100).toFixed(1)+"%";
  el.querySelector(".meta").innerHTML=meta.join("");
}
function taskMeta(t){
  const meta=[];
  if(t.state==="running"||t.state==="stalled"){meta.push(`<span><b>${Math.round(t.progress*100)}%</b></span>`);
    if(t.step) meta.push(`<span>step ${t.step.toLocaleString()} / ${t.total.toLocaleString()}</span>`);
    if(t.speed) meta.push(`<span>${t.speed} reviews/s</span>`);
    const e=eta(t.eta_seconds); if(e&&t.progress<1) meta.push(`<span><b>${e}</b></span>`);}
  if(t.note) meta.push(`<span>${t.note}</span>`);
  if(t.val_pool!=null) meta.push(`<span>Practice set <b>${pct(t.val_pool)}</b></span>`);
  if(t.test!=null) meta.push(`<span>Test <b>${pct(t.test)}</b></span>`);
  return meta;
}
async function tick(){
  try{
    const s=await (await fetch("/api/status",{cache:"no-store"})).json();
    const box=document.getElementById("tasks");
    for(const t of s.tasks){const el=ensureCard(t.id,box); el.classList.toggle("waiting",t.state==="waiting");
      fill(el,t.title,ICON[t.state]||t.state,t.what,t.progress,taskMeta(t));}
    const sp=s.spend.metered, f=sp==null?0:Math.min(sp/s.budget,1);
    fill(ensureCard("budget",document.getElementById("budget")),"Modal credit used",
      sp==null?"checking…":"$"+sp.toFixed(2)+" of $"+s.budget,"",f,
      ["<span>Covered by your free credits</span>"].concat(s.spend.checked?[`<span>checked ${s.spend.checked}</span>`]:[]));
    const running=s.tasks.filter(t=>t.state==="running").length, done=s.tasks.filter(t=>t.state==="done").length;
    document.getElementById("updated").textContent=`${done} of ${s.tasks.length} done · ${running} running · updated ${s.updated} (refreshes every 5 s)`;
  }catch(e){document.getElementById("updated").textContent="Can't reach the dashboard server. Is it still running?"}
}
tick(); setInterval(tick,5000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            body, ctype = json.dumps(status()).encode(), "application/json"
        else:
            body, ctype = PAGE.encode(), "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # keep the terminal quiet
        pass


if __name__ == "__main__":
    threading.Thread(target=refresh_spend, daemon=True).start()
    print(f"dashboard on http://localhost:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
