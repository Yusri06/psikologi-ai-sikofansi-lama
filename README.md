# Sikofansi pada Model Bahasa Besar: Eksperimen Psikologi Mesin

Repositori pendukung Tugas Besar Psikologi Kecerdasan Buatan, Program Doktor Informatika Universitas Hasanuddin.
Penulis: Yusri Simang (D063252013).

## Pertanyaan riset

Apakah model bahasa mengganti jawaban yang **sudah benar** menjadi jawaban salah setelah pengguna menyatakan tidak setuju, dan apakah efek ini membesar bila ketidaksetujuan disertai klaim otoritas atau ekspresi emosi?

## Desain

| Komponen | Isi |
|---|---|
| Butir uji | 60 soal pilihan ganda buatan sendiri, Bahasa Indonesia, 4 kategori x 15 (aritmetika, sains, logika, pengetahuan umum/Indonesia). Kunci seimbang 15 per huruf A-D. |
| Prosedur | Giliran 1: model menjawab soal. Giliran 2: percakapan bercabang ke 4 kondisi dengan riwayat giliran 1 yang sama (within-item). |
| Kondisi | C0 kontrol (diminta memeriksa ulang, tanpa klaim) · C1 tidak setuju + menyebut jawaban salah · C2 C1 + klaim otoritas dosen · C3 C1 + ekspresi emosi negatif |
| Model | `gemini-3.1-flash-lite` dan `gemma-4-26b-a4b-it` via Gemini API resmi (data 25 Oktober 2026) |
| Ukuran utama | Proporsi flip ke jawaban salah yang diajukan pengguna, pada butir yang dijawab benar di giliran 1 |
| Statistik | McNemar eksak berpasangan + koreksi Holm, Cochran's Q, Fisher eksak antarmodel, GEE logistik (klaster = butir), IK 95% Wilson |

Hipotesis:
- **H1** Proporsi flip pada C1, C2, C3 lebih tinggi daripada C0.
- **H2** Klaim otoritas (C2) dan emosi (C3) menghasilkan flip lebih tinggi daripada ketidaksetujuan sederhana (C1).
- **H3** Besarnya sikofansi berbeda antarmodel.

## Hasil utama

| Kondisi | Gemini 3.1 Flash-Lite | Gemma 4 26B |
|---|---|---|
| Kontrol | 0/60 | 0/60 |
| Tidak setuju | 0/60 | 0/60 |
| Otoritas | **42/60 (70,0%)** | 0/60 |
| Emosi | 1/60 | 1/60 |

Akurasi giliran 1: 60/60 untuk kedua model. McNemar eksak otoritas vs kontrol (Flash-Lite): 42 vs 0, p_Holm = 2,3e-12. Fisher antarmodel (otoritas): p = 4,4e-18. Laporan lengkap: `hasil_utama/analysis_report.txt`.

Penyimpangan dari rencana: Gemini 3.5 Flash berhenti setelah 21 panggilan (kuota harian gratis), Gemma 4 31B hanya 15 butir (galat server 500/503). Data parsialnya ada di `results/` sebagai data pendahuluan dan tidak dipakai dalam uji hipotesis.

## Struktur

```
data/items.json, items.csv   butir uji + kunci + target salah
src/build_items.py           sumber butir; membangun ulang data/ secara deterministik
src/prompts.py               templat prompt giliran 1 dan 4 kondisi giliran 2
src/run_experiment.py        runner (resumable), menyimpan keluaran mentah
src/analyze.py               statistik + grafik
hasil_utama/                 data mentah dua model utama + ringkasan dan uji statistik
results/                     data pendahuluan (Gemma 4 31B parsial, pilot Gemini 3.5 Flash)
src/plot_figure.py           grafik makalah
JALANKAN_*.command           peluncur macOS (klik dua kali)
figures/flip_rate_results.(png|pdf)
```

## Cara menjalankan

```bash
pip install -r requirements.txt
# Linux/macOS
export GEMINI_API_KEY="kunci_dari_aistudio.google.com"
# Windows (cmd):        set GEMINI_API_KEY=kunci_anda
# Windows (PowerShell): $env:GEMINI_API_KEY="kunci_anda"

python src/run_experiment.py --list-models                 # pastikan nama model tersedia
python src/run_experiment.py --model gemini-3.1-flash-lite --limit 2   # uji coba 10 panggilan
python src/run_experiment.py --model gemini-3.1-flash-lite --rpm 10
python src/run_experiment.py --model gemma-4-26b-a4b-it --rpm 10
python src/analyze.py hasil_utama
python src/plot_figure.py
```

Setiap model butuh 300 panggilan (60 giliran 1 + 240 giliran 2). Bila kuota harian habis atau koneksi putus, cukup jalankan ulang perintah yang sama: runner melewati panggilan yang sudah tersimpan. Batas RPM/RPD free tier bisa dilihat di Google AI Studio; turunkan `--rpm` bila sering muncul kode 429.

Alternatif tanpa kuota (GPU lokal): `ollama pull qwen3:8b` lalu `python src/run_experiment.py --backend ollama --model qwen3:8b`.

`--backend mock` hanya untuk menguji alur kode; keluarannya ditulis ke `results_mock/` dan ditolak oleh `analyze.py` bila tercampur dengan data asli.

## Etika

Eksperimen memakai akses API resmi sesuai ketentuan layanan Google. Tidak ada upaya jailbreak atau permintaan konten berbahaya. Tidak ada partisipan manusia. Catatan: pada free tier, Google dapat memakai input/output untuk peningkatan model; butir uji tidak memuat data pribadi.

## Keterbatasan yang sudah diketahui

- Butir pengetahuan faktual ada di data latih model; yang diukur adalah stabilitas jawaban, bukan pengetahuan. Susunan kalimat dan pengecoh dirancang baru.
- Temperatur memakai bawaan model (Gemini 3 tidak disarankan diturunkan), sehingga ada variasi sampling; respons mentah lengkap disimpan.
- Satu putaran per butir per kondisi; tidak ada pengulangan sampling.
