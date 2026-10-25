"""Runner eksperimen sikofansi (dapat dilanjutkan bila terputus).

Desain: untuk setiap model dan butir, giliran 1 dijalankan sekali; lalu
percakapan bercabang ke 4 kondisi giliran 2 dengan riwayat giliran 1 yang sama
(desain within-item). Semua keluaran mentah disimpan ke results/raw_<model>.jsonl.

Contoh:
  export GEMINI_API_KEY=...                       # Windows: set GEMINI_API_KEY=...
  python src/run_experiment.py --list-models
  python src/run_experiment.py --model gemini-3.5-flash --rpm 8
  python src/run_experiment.py --model gemma-4-31b-it --rpm 20
  python src/run_experiment.py --backend ollama --model qwen3:8b   # alternatif lokal
  python src/run_experiment.py --backend mock --model mock          # uji alur tanpa kuota
"""
import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompts import CONDITIONS, turn1, turn2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ANS_RE = re.compile(r"JAWABAN\s*[:：]\s*\**\s*\(?([ABCD])\b", re.IGNORECASE)


def parse_answer(text):
    """Ambil huruf dari baris 'JAWABAN: X' terakhir; None bila tidak ada."""
    if not text:
        return None
    m = ANS_RE.findall(text)
    return m[-1].upper() if m else None


class QuotaExhausted(Exception):
    """Kuota harian habis; hentikan model ini."""


class SkipCall(Exception):
    """Panggilan dilewati sementara; diulang pada putaran berikutnya."""


# ---------------------------------------------------------------- backends
class Gemini:
    def __init__(self, model, temperature):
        self.key = os.environ.get("GEMINI_API_KEY")
        if not self.key:
            sys.exit("GEMINI_API_KEY belum diset.")
        self.model, self.temperature = model, temperature

    def chat(self, messages):
        contents = [{"role": "user" if m["role"] == "user" else "model",
                     "parts": [{"text": m["content"]}]} for m in messages]
        body = {"contents": contents, "generationConfig": {"maxOutputTokens": 8192}}
        if self.temperature is not None:
            body["generationConfig"]["temperature"] = self.temperature
        for attempt in range(7):
            try:
                r = requests.post(GEMINI_URL.format(model=self.model), json=body, timeout=180,
                                  headers={"x-goog-api-key": self.key})
            except requests.RequestException as e:
                print(f"  [koneksi] {type(e).__name__}, tunggu 15s ...", flush=True)
                time.sleep(15)
                continue
            if r.status_code == 429:
                msg = r.text
                if "PerDay" in msg or "per_day" in msg.lower() or "daily" in msg.lower():
                    print("  [429] KUOTA HARIAN model ini habis:", msg[:400], flush=True)
                    raise QuotaExhausted(msg[:400])
            if r.status_code in (429, 500, 502, 503, 504):
                wait = min(60, 5 * 2 ** attempt)
                print(f"  [{r.status_code}] server sibuk, tunggu {wait}s ...", flush=True)
                time.sleep(wait)
                continue
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            data = r.json()
            cands = data.get("candidates") or []
            if not cands:
                return "", {"blocked": data.get("promptFeedback")}
            parts = cands[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            return text, {"finish": cands[0].get("finishReason"), "usage": data.get("usageMetadata")}
        raise SkipCall("server terus gagal")

    @staticmethod
    def list_models():
        key = os.environ.get("GEMINI_API_KEY") or sys.exit("GEMINI_API_KEY belum diset.")
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                         headers={"x-goog-api-key": key}, params={"pageSize": 200}, timeout=60)
        r.raise_for_status()
        for m in r.json().get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                print(m.get("name", "?").replace("models/", ""), "-", m.get("displayName", ""))


class Ollama:
    def __init__(self, model, temperature, host="http://localhost:11434"):
        self.model, self.temperature, self.host = model, temperature, host

    def chat(self, messages):
        body = {"model": self.model, "messages": messages, "stream": False}
        if self.temperature is not None:
            body["options"] = {"temperature": self.temperature}
        r = requests.post(f"{self.host}/api/chat", json=body, timeout=600)
        r.raise_for_status()
        text = r.json()["message"]["content"]
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
        return text, {}


class Mock:
    """Backend palsu untuk menguji alur kode. Datanya TIDAK boleh dipakai di makalah."""
    def __init__(self, *_):
        self.rng = random.Random(0)

    def chat(self, messages):
        return f"Alasan uji. JAWABAN: {self.rng.choice('ABCD')}", {"mock": True}


# ---------------------------------------------------------------- main loop
def load_done(path):
    done = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                if not (rec.get("response") or "").strip():
                    continue  # respons kosong (mis. MAX_TOKENS): ulangi
                done[(rec["item_id"], rec["stage"])] = rec
    return done


def main():
    try:
        _main()
    except QuotaExhausted:
        print("Berhenti: kuota harian model ini habis. Progres tersimpan.")
        sys.exit(4)


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["gemini", "ollama", "mock"], default="gemini")
    ap.add_argument("--model")
    ap.add_argument("--rpm", type=float, default=8, help="batas permintaan per menit")
    ap.add_argument("--temperature", type=float, default=None,
                    help="default: bawaan model (Gemini 3 disarankan tidak diturunkan)")
    ap.add_argument("--limit", type=int, default=None, help="hanya N butir pertama (uji coba)")
    ap.add_argument("--list-models", action="store_true")
    a = ap.parse_args()

    if a.list_models:
        Gemini.list_models()
        return
    if not a.model:
        sys.exit("--model wajib diisi")

    client = {"gemini": Gemini, "ollama": Ollama, "mock": Mock}[a.backend](a.model, a.temperature)
    items = json.loads((ROOT / "data" / "items.json").read_text(encoding="utf-8"))[: a.limit]
    outdir = ROOT / ("results_mock" if a.backend == "mock" else "results")
    outdir.mkdir(exist_ok=True)
    out = outdir / f"raw_{re.sub(r'[^A-Za-z0-9._-]', '_', a.model)}.jsonl"
    done = load_done(out)
    gap = 60.0 / a.rpm if a.backend == "gemini" else 0
    conds = list(CONDITIONS)
    rng = random.Random(42)
    total = len(items) * (1 + len(conds))
    print(f"Model {a.model}: {len(done)}/{total} panggilan sudah ada di {out}")

    def call(messages):
        t0 = time.time()
        text, meta = client.chat(messages)
        time.sleep(max(0.0, gap - (time.time() - t0)))
        return text, meta

    skipped = []
    with open(out, "a", encoding="utf-8") as f:
        def save(rec):
            rec.update(model=a.model, backend=a.backend, temperature=a.temperature,
                       timestamp=datetime.now(timezone.utc).isoformat())
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            done[(rec["item_id"], rec["stage"])] = rec

        for n, it in enumerate(items, 1):
            p1 = turn1(it)
            if (it["item_id"], "T1") not in done:
                try:
                    text, meta = call([{"role": "user", "content": p1}])
                except SkipCall:
                    skipped.append(it["item_id"])
                    print(f"  [{n}/{len(items)}] {it['item_id']} DILEWATI (diulang nanti)", flush=True)
                    continue
                save({"item_id": it["item_id"], "stage": "T1", "prompt": p1, "response": text,
                      "answer": parse_answer(text), "kunci": it["kunci"],
                      "target_salah": it["target_salah"], "meta": meta})
            t1 = done[(it["item_id"], "T1")]
            order = conds[:]
            rng.shuffle(order)
            for c in order:
                if (it["item_id"], c) in done:
                    continue
                p2 = turn2(it, c)
                msgs = [{"role": "user", "content": p1},
                        {"role": "assistant", "content": t1["response"]},
                        {"role": "user", "content": p2}]
                try:
                    text, meta = call(msgs)
                except SkipCall:
                    skipped.append(f"{it['item_id']}/{c}")
                    continue
                save({"item_id": it["item_id"], "stage": c, "prompt": p2, "response": text,
                      "answer": parse_answer(text), "turn1_answer": t1["answer"], "kunci": it["kunci"],
                      "target_salah": it["target_salah"], "meta": meta})
            print(f"  [{n}/{len(items)}] {it['item_id']} selesai", flush=True)
    print(f"Selesai: {len(done)}/{total} panggilan tersimpan di {out}")
    if skipped:
        print(f"Dilewati {len(skipped)} panggilan karena server sibuk; jalankan ulang untuk melengkapi.")
        sys.exit(3)


if __name__ == "__main__":
    main()
