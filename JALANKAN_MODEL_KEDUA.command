#!/bin/bash
# Model kedua pengganti Gemma 31B. Klik dua kali di Finder. Jendela lain JANGAN ditutup.
cd "$(dirname "$0")"
source .venv/bin/activate
echo "=== Model kedua: Gemini Flash-Lite ==="
echo "Tempel (paste) GEMINI API KEY lalu Enter (tulisan tidak tampil):"
read -s GEMINI_API_KEY; export GEMINI_API_KEY; echo ""
for M in gemini-3.1-flash-lite gemini-2.5-flash-lite gemini-3.5-flash-lite; do
  grep -q "^$M " results/models_available.txt || continue
  echo "Mencoba $M ..." | tee -a results/models_used.txt
  for pass in 1 2 3 4 5; do
    echo "--- $M putaran $pass ---"
    python src/run_experiment.py --model "$M" --rpm 10 2>&1 | tee -a "results/log_$M.txt"
    rc=${PIPESTATUS[0]}
    [ "$rc" = "0" ] && { echo "=== $M SELESAI. Kembali ke chat Claude. ==="; read -p "Enter untuk menutup"; exit 0; }
    [ "$rc" = "4" ] && { echo "Kuota harian $M habis, coba model berikutnya."; break; }
    sleep 60
  done
done
echo "Semua model Flash-Lite kehabisan kuota. Kabari Claude."
read -p "Enter untuk menutup"
