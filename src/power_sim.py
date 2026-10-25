"""Simulasi daya uji McNemar eksak untuk desain eksperimen (dilaporkan di makalah).

Asumsi: n pasangan butir (benar di giliran 1), proporsi flip kontrol p0,
proporsi flip kondisi pushback p1, flip antarkondisi independen.
Jalankan: python src/power_sim.py
"""
import numpy as np
from scipy.stats import binomtest


def power(n, p0, p1, alpha, reps=3000, seed=2):
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(reps):
        a = rng.random(n) < p0
        b = rng.random(n) < p1
        n01, n10 = int((~a & b).sum()), int((a & ~b).sum())
        if n01 + n10 > 0 and binomtest(n01, n01 + n10, 0.5).pvalue < alpha:
            hits += 1
    return hits / reps


if __name__ == "__main__":
    print("n   p0    p1    daya(alpha=0.01)  daya(alpha=0.05)")
    for n in (45, 50, 55):
        for p1 in (0.10, 0.15, 0.20, 0.25, 0.30, 0.40):
            print(f"{n:<3} 0.02  {p1:.2f}  {power(n, .02, p1, .01):.2f}              {power(n, .02, p1, .05):.2f}")
