"""Grafik utama makalah dari hasil_utama/summary_flip.csv."""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "hasil_utama")
d = pd.read_csv(folder / "summary_flip.csv")
conds = ["C0_kontrol", "C1_tidak_setuju", "C2_otoritas", "C3_emosi"]
lab = ["Kontrol", "Tidak\nsetuju", "Otoritas", "Emosi"]
names = {"gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite", "gemma-4-26b-a4b-it": "Gemma 4 26B (MoE)"}
colors = {"gemini-3.1-flash-lite": "#2b6cb0", "gemma-4-26b-a4b-it": "#c05621"}
fig, ax = plt.subplots(figsize=(3.5, 2.5), dpi=300)
models = list(names)
w = 0.38
x = np.arange(len(conds))
for i, m in enumerate(models):
    s = d[d.model == m].set_index("kondisi").reindex(conds)
    pos = x + (i - 0.5) * w
    err = np.vstack([s.rate - s.ci_lo, s.ci_hi - s.rate])
    ax.bar(pos, s.rate * 100, w, yerr=err * 100, capsize=2, color=colors[m], label=names[m],
           error_kw={"elinewidth": 0.7})
    for p, k, n in zip(pos, s.flip_target, s.n):
        ax.text(p, s.rate.loc[conds[list(pos).index(p)]] * 100 + (err[1][list(pos).index(p)] * 100) + 2,
                f"{k}/{n}", ha="center", fontsize=5.5)
ax.set_xticks(x, lab, fontsize=7)
ax.set_ylabel("Flip ke jawaban salah (%)", fontsize=7)
ax.set_ylim(0, 100)
ax.tick_params(axis="y", labelsize=7)
ax.legend(fontsize=6, frameon=False, loc="upper left")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
out = ROOT / "figures"
out.mkdir(exist_ok=True)
fig.savefig(out / "flip_rate_results.pdf")
fig.savefig(out / "flip_rate_results.png")
print("ok")
