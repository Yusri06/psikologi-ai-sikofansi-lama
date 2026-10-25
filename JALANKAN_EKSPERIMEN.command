#!/bin/bash
# Klik dua kali file ini di Finder. Menjalankan eksperimen sikofansi + analisis.
cd "$(dirname "$0")"
echo "=== Eksperimen Sikofansi - Tugas Besar Psikologi AI ==="
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3 belum ada. Install dari https://www.python.org/downloads/ lalu klik file ini lagi."; read -p "Tekan Enter untuk keluar"; exit 1
fi
if [ ! -d .venv ]; then
  echo "[1/4] Menyiapkan lingkungan Python (sekali saja)..."
  python3 -m venv .venv || { echo "Gagal membuat venv"; read -p "Enter"; exit 1; }
fi
source .venv/bin/activate
pip install -q --upgrade pip >/dev/null 2>&1
pip install -q -r requirements.txt || { echo "Gagal install paket"; read -p "Enter"; exit 1; }

if [ -z "$GEMINI_API_KEY" ]; then
  echo ""
  echo "Tempel (paste) GEMINI API KEY Anda lalu tekan Enter."
  echo "(Ambil di https://aistudio.google.com/apikey . Tulisannya tidak akan tampil; itu normal.)"
  read -s GEMINI_API_KEY; export GEMINI_API_KEY; echo ""
fi

mkdir -p results
echo "[2/4] Mengecek daftar model..."
python src/run_experiment.py --list-models > results/models_available.txt 2>&1 || { cat results/models_available.txt; echo "API key ditolak / tidak valid."; read -p "Enter"; exit 1; }

pick() { for m in "$@"; do grep -q "^$m " results/models_available.txt && { echo "$m"; return; }; done; }
GEMMA=$(pick gemma-4-31b-it gemma-4-26b-a4b-it gemma-3-27b-it)
GEMMA2=$(pick gemma-4-26b-a4b-it gemma-3-27b-it)
echo "Model terpilih: $GEMMA dan $GEMMA2" | tee results/models_used.txt

run_model() {  # $1=model $2=rpm ; ulangi sampai lengkap (maks 5 putaran)
  for pass in 1 2 3 4 5; do
    echo "--- $1 putaran $pass ---"
    python src/run_experiment.py --model "$1" --rpm "$2" 2>&1
    rc=${PIPESTATUS[0]}
    [ "$rc" = "0" ] && return 0
    [ "$rc" = "4" ] && { echo "Kuota harian $1 habis, lanjut ke langkah berikutnya."; return 1; }
    echo "Masih ada yang terlewat, istirahat 60 detik lalu diulang..."; sleep 60
  done
}
echo "[3/4] Menjalankan $GEMMA2 dan $GEMMA BERSAMAAN (masing-masing 300 panggilan)..."
echo "     Progres tiap model ditulis ke results/log_<model>.txt"
run_model "$GEMMA2" 10 > "results/log_$GEMMA2.txt" 2>&1 &
P1=$!
run_model "$GEMMA" 10 > "results/log_$GEMMA.txt" 2>&1 &
P2=$!
while kill -0 $P1 2>/dev/null || kill -0 $P2 2>/dev/null; do
  n1=$(wc -l < "results/raw_$GEMMA2.jsonl" 2>/dev/null || echo 0)
  n2=$(wc -l < "results/raw_$GEMMA.jsonl" 2>/dev/null || echo 0)
  echo "$(date +%H:%M)  $GEMMA2: $n1 baris | $GEMMA: $n2 baris (target masing-masing 300)"
  sleep 60
done
wait

echo "[4/4] Analisis statistik..."
python src/analyze.py 2>&1 | tee results/log_analyze.txt
echo ""
echo "=== SELESAI. Kembali ke chat Claude dan bilang 'sudah selesai'. ==="
read -p "Tekan Enter untuk menutup"
