# Catatan Arsitektur Sistem — StockAlpha

> Dokumen ini menjelaskan secara lengkap bagaimana seluruh komponen aplikasi StockAlpha bekerja, saling terhubung, menyimpan data, dan mengirimkan informasi. Ditulis agar bisa dipahami siapa saja, termasuk yang belum familiar dengan kode.

---

## 1. Gambaran Besar (Big Picture)

Bayangkan aplikasi ini seperti sebuah restoran:

| Komponen | Analogi Restoran |
|---|---|
| Browser (frontend) | Pelanggan yang memesan dan melihat menu |
| Flask server (backend) | Dapur + pelayan |
| yfinance | Supplier bahan baku (data dari Yahoo Finance) |
| SQLite database | Lemari es / gudang penyimpanan catatan |

Ketika kamu membuka browser dan melihat grafik saham, ini yang terjadi:
1. Browser kirim permintaan ke server ("tolong ambilkan data saham BBCA")
2. Server tanya ke Yahoo Finance lewat internet ("berikan data harga BBCA")
3. Yahoo Finance kirim balik data mentah
4. Server olah data itu (hitung indikator teknikal, rasio, dll)
5. Server kirim hasilnya ke browser dalam format JSON
6. Browser gambar chart dan tampilkan ke layar

---

## 2. Struktur Folder

```
claude-test-stock-check-a1/
├── wsgi.py                          ← Titik masuk untuk server produksi
├── src/
│   └── stock_checker/
│       ├── app.py                   ← Buat Flask app, daftarkan semua blueprint
│       ├── fetcher.py               ← Ambil data dari yfinance
│       ├── indicators.py            ← Hitung SMA, RSI
│       ├── alpha/                   ← Modul utama fitur analisis
│       │   ├── __init__.py          ← Inisialisasi modul, buat tabel database
│       │   ├── models/
│       │   │   ├── database.py      ← Objek SQLAlchemy (db)
│       │   │   └── schemas.py       ← Definisi tabel database
│       │   ├── routes/              ← URL endpoint API
│       │   ├── services/            ← Logika bisnis (ambil + olah data)
│       │   ├── calculations/        ← Rumus perhitungan murni
│       │   ├── static/alpha/        ← File frontend (JS, CSS)
│       │   └── templates/alpha/     ← HTML template
└── instance/
    └── alpha.db                     ← File database SQLite (dibuat otomatis)
```

---

## 3. Database: Bagaimana Dibuat dan Digunakan

### 3.1 Cara Kerjanya (Bahasa Awam)

Database di aplikasi ini menggunakan **SQLite** — yaitu database yang disimpan sebagai **satu file** di komputer (`instance/alpha.db`). Tidak perlu install MySQL atau PostgreSQL terpisah. File ini otomatis dibuat saat server pertama kali dijalankan.

Prosesnya:
1. Kamu jalankan server (`uv run stock-checker-web`)
2. `app.py` memanggil `init_alpha(app)`
3. `init_alpha` di `alpha/__init__.py` memberi tahu SQLAlchemy: *"simpan database di sini: `instance/alpha.db`"*
4. Perintah `db.create_all()` membaca semua definisi tabel dari `schemas.py` dan membuat tabel yang belum ada
5. File `alpha.db` tercipta (kalau belum ada) — sekarang database siap dipakai

### 3.2 Siapa yang Membuat File Database?

```python
# alpha/__init__.py — fungsi init_alpha()
instance_path = os.path.join(app.instance_path, "alpha.db")
os.makedirs(app.instance_path, exist_ok=True)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{instance_path}"

db.init_app(app)

with app.app_context():
    db.create_all()   # ← INI yang membuat tabel
```

`db.create_all()` hanya membuat tabel yang **belum ada**. Kalau tabel sudah ada, perintah ini tidak menghapus atau mengubah data yang sudah tersimpan. Aman dijalankan berulang kali.

### 3.3 Tabel-Tabel Database

Ada **6 tabel** di database, masing-masing untuk menyimpan jenis data yang berbeda:

#### Tabel `watchlist` — Daftar Pantau
Menyimpan koleksi saham yang kamu buat (misal: "Porto Growth", "Bank-bank").

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | Integer | Nomor unik otomatis |
| name | String(100) | Nama watchlist |
| description | Text | Deskripsi (opsional) |
| created_at | DateTime | Waktu dibuat |
| updated_at | DateTime | Waktu terakhir diubah |

#### Tabel `watchlist_item` — Isi Watchlist
Setiap baris = satu saham di dalam sebuah watchlist.

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | Integer | Nomor unik otomatis |
| watchlist_id | Integer | Referensi ke tabel watchlist (FK) |
| ticker | String(20) | Kode saham, misal "BBCA.JK" |
| category | String(50) | Kategori, misal "bank" |
| added_at | DateTime | Kapan ditambahkan |

> **Catatan**: Kalau sebuah watchlist dihapus, semua item di dalamnya ikut terhapus otomatis (cascade delete).

#### Tabel `analysis_note` — Catatan Analisis
Catatan teks bebas yang kamu tulis untuk suatu saham.

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | Integer | Nomor unik |
| ticker | String(20) | Kode saham (diindeks untuk pencarian cepat) |
| title | String(200) | Judul catatan |
| content | Text | Isi catatan (markdown) |
| tags | String(500) | Tag dipisah koma, misal "bank,dividen" |
| created_at | DateTime | Waktu dibuat |
| updated_at | DateTime | Waktu diubah |

> Tags disimpan sebagai teks biasa dipisah koma, tapi saat dibaca (`to_dict()`) otomatis diubah jadi list Python: `["bank", "dividen"]`.

#### Tabel `ratio_snapshot` — Snapshot Rasio Keuangan
Rekaman rasio keuangan suatu saham pada tanggal tertentu (untuk tracking historis).

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | Integer | Nomor unik |
| ticker | String(20) | Kode saham |
| snapshot_date | Date | Tanggal snapshot |
| data_json | Text | Data rasio lengkap dalam format JSON |
| created_at | DateTime | Waktu disimpan |

> Data kompleks (banyak kolom) disimpan sebagai JSON string di kolom `data_json`. Saat dibaca, string ini di-parse balik ke dict Python.

#### Tabel `valuation_result` — Hasil Valuasi
Menyimpan hasil perhitungan model valuasi (DCF, PBV, DDM, dll).

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | Integer | Nomor unik |
| ticker | String(20) | Kode saham |
| model_type | String(20) | Jenis model: "dcf", "pbv", "ddm", "roe" |
| assumptions_json | Text | Asumsi yang dipakai (WACC, dll) dalam JSON |
| results_json | Text | Hasil perhitungan dalam JSON |
| created_at | DateTime | Waktu dihitung |

#### Tabel `comparison_session` — Sesi Perbandingan
Menyimpan hasil perbandingan antar saham.

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | Integer | Nomor unik |
| name | String(200) | Nama sesi |
| tickers_json | Text | Daftar ticker dalam JSON |
| results_json | Text | Hasil perbandingan dalam JSON |
| created_at | DateTime | Waktu dibuat |

---

## 4. Arsitektur Backend (Server)

### 4.1 Layer-layer Backend

Backend dibagi menjadi **4 lapisan** yang bekerja dari atas ke bawah:

```
[Browser] ──HTTP──► [Routes] ──► [Services] ──► [Calculations]
                                     │
                                     ▼
                              [yfinance API] + [Database]
```

| Layer | Folder | Tugas |
|---|---|---|
| Routes | `routes/` | Terima request HTTP, kirim response JSON |
| Services | `services/` | Koordinasi: ambil data, panggil kalkulasi |
| Calculations | `calculations/` | Rumus murni — tidak tahu soal HTTP sama sekali |
| Models | `models/` | Definisi tabel database |

### 4.2 Routes (Endpoint API)

Setiap route adalah "pintu" ke server. Browser mengirim request ke URL tertentu, server balas dengan JSON.

| Blueprint | Prefix | Endpoint | Fungsi |
|---|---|---|---|
| dashboard | `/alpha/` | `GET /` | Halaman utama (HTML) |
| dashboard | `/alpha/` | `POST /api/price-history` | Data harga + indikator |
| dashboard | `/alpha/` | `GET /api/watchlists` | Ambil semua watchlist |
| dashboard | `/alpha/` | `POST /api/watchlists` | Buat watchlist baru |
| dashboard | `/alpha/` | `GET /api/notes` | Ambil semua catatan |
| financials | `/alpha/` | `POST /api/financials` | Laporan keuangan + rasio |
| trends | `/alpha/` | `POST /api/trends` | Analisis tren pertumbuhan |
| modelling | `/alpha/` | `POST /api/model/dcf` | Valuasi DCF |
| modelling | `/alpha/` | `POST /api/model/pbv` | Valuasi PBV |
| modelling | `/alpha/` | `POST /api/model/ddm` | Valuasi DDM |
| modelling | `/alpha/` | `POST /api/model/roe` | Valuasi ROE Sustainable |
| comparison | `/alpha/` | `POST /api/compare` | Bandingkan multiple saham |
| scores | `/alpha/` | `POST /api/scores` | Hitung Quality/Value/Risk Score |
| export | `/alpha/` | `POST /api/export/...` | Export data |

### 4.3 Cara Blueprint Didaftarkan

Flask menggunakan **Blueprint** untuk memisahkan kode per fitur. Semua blueprint didaftarkan di `alpha/__init__.py`:

```
app.py
  └── init_alpha(app)
        └── create_alpha_blueprint()
              ├── register dashboard.bp    → /alpha/
              ├── register comparison.bp   → /alpha/
              ├── register financials.bp   → /alpha/
              ├── register trends.bp       → /alpha/
              ├── register modelling.bp    → /alpha/
              ├── register portfolio.bp    → /alpha/
              ├── register export.bp       → /alpha/
              └── register scores.bp      → /alpha/
```

---

## 5. Alur Data Lengkap

### 5.1 Alur: User Lihat Grafik Harga

```
1. User buka browser → http://localhost:5000/alpha/
2. Browser minta HTML → Server kirim index.html
3. app.js diload → JS mulai jalan di browser

4. app.js POST /alpha/api/price-history  { ticker: "BBCA.JK", period: "1y" }
                        ↓
5. routes/dashboard.py terima request
                        ↓
6. services/data_fetcher.py panggil yfinance.Ticker("BBCA.JK")
   yfinance ambil data dari Yahoo Finance (internet)
                        ↓
7. Terima DataFrame: tanggal, open, high, low, close, volume
                        ↓
8. calculations/ hitung:
   - SMA 20, SMA 50, SMA 200
   - EMA 20
   - RSI 14
   - MACD (12,26,9)
   - Bollinger Bands
                        ↓
9. Service susun response JSON berisi semua data
                        ↓
10. Route kirim response JSON ke browser
                        ↓
11. app.js terima JSON → panggil Plotly.js → gambar chart interaktif
```

### 5.2 Alur: User Hitung Score Saham

```
1. User klik tombol Analisis di halaman Detail
2. app.js POST /alpha/api/scores  { ticker: "BBCA.JK" }
                        ↓
3. routes/scores.py terima request
                        ↓
4. services/scores.py panggil:
   ├── get_financial_analysis("BBCA.JK")   → data rasio keuangan
   └── get_trend_analysis("BBCA.JK")       → data tren pertumbuhan
   (Kedua fungsi ini juga panggil yfinance)
                        ↓
5. calculations/scores.py hitung:
   ├── Quality Score  (ROE, ROA, margin, CAGR) → 0-100
   ├── Valuation Score (PER, PBV, EV/EBITDA)  → 0-100
   └── Risk Score     (DER, Beta, Current Ratio) → 0-100
                        ↓
6. Composite = 35% Quality + 35% Valuation + 30% Risk
   Recommendation: Strong Buy / Buy / Hold / Avoid
                        ↓
7. Response JSON → browser → tampil gauge dan badge
```

### 5.3 Alur: User Simpan Watchlist

```
1. User klik "Buat Watchlist" → isi form → submit
2. app.js POST /alpha/api/watchlists  { name: "Porto Growth", tickers: [...] }
                        ↓
3. routes/dashboard.py terima
                        ↓
4. services/ buat objek Watchlist (SQLAlchemy model)
                        ↓
5. db.session.add(watchlist)
   db.session.commit()
   → Data ditulis ke file alpha.db
                        ↓
6. Response: { id: 1, name: "Porto Growth", ... }
                        ↓
7. app.js perbarui tampilan watchlist di sidebar
```

### 5.4 Alur: Data Tidak Disimpan (Stateless)

**Penting**: Sebagian besar data di StockAlpha **tidak disimpan** ke database. Setiap kali kamu minta analisis, server selalu ambil data fresh dari Yahoo Finance.

Yang **disimpan** ke database:
- ✅ Watchlist dan isinya
- ✅ Catatan analisis (notes)
- ✅ Snapshot rasio (kalau fitur ini dipakai)
- ✅ Hasil valuasi (kalau disimpan manual)

Yang **tidak disimpan** (dihitung ulang tiap request):
- ❌ Data harga saham (selalu fresh dari Yahoo)
- ❌ Indikator teknikal (dihitung di server setiap request)
- ❌ Laporan keuangan (selalu live dari Yahoo Finance)
- ❌ Score (dihitung ulang dari data live)

---

## 6. Frontend (Browser)

### 6.1 Arsitektur SPA

Frontend adalah **Single Page Application (SPA)** — artinya cuma ada **satu halaman HTML** (`index.html`) dan semua navigasi dilakukan oleh JavaScript tanpa reload halaman.

```
Browser load /alpha/
  └── index.html (sekali saja)
        └── app.js (baca URL hash untuk tahu halaman mana)
              ├── #dashboard  → renderDashboard()
              ├── #detail     → renderDetail()
              ├── #compare    → renderCompare()
              ├── #model      → renderModel()
              ├── #trends     → renderTrends()
              └── #notes      → renderNotes()
```

Ketika kamu klik "Detail" di navbar, URL berubah dari `#dashboard` ke `#detail` — app.js mendeteksi perubahan hash dan merender konten baru tanpa reload.

### 6.2 Komunikasi Frontend ↔ Backend

Semua komunikasi melalui **HTTP API** (fetch/AJAX):

```javascript
// Contoh: ambil data harga
const res = await fetch('/alpha/api/price-history', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker: 'BBCA.JK', period: '1y' })
});
const data = await res.json();
// → data: { dates: [...], closes: [...], sma20: [...], rsi: [...], ... }
```

Format yang dipakai: **JSON** (teks terstruktur, bisa dibaca manusia dan mesin).

### 6.3 File-file Frontend

| File | Isi |
|---|---|
| `static/alpha/app.js` | Semua logika UI, routing, render halaman |
| `static/alpha/styles.css` | Tampilan / desain |
| `static/alpha/components/charts.js` | Helper render chart Plotly |
| `static/alpha/components/tables.js` | Helper render tabel |
| `static/alpha/components/forms.js` | Helper render form input |
| `static/alpha/components/router.js` | Hash-based router |
| `static/alpha/html2canvas.min.js` | Library screenshot |

---

## 7. Scoring Engine

### 7.1 Tiga Dimensi Score

Setiap saham dinilai dari tiga sudut pandang, masing-masing menghasilkan nilai 0–100:

**Quality Score** — Seberapa bagus bisnisnya?
- ROE (Return on Equity) — efisiensi menggunakan modal sendiri
- ROA (Return on Assets) — efisiensi aset
- Net Profit Margin — margin keuntungan bersih
- Gross Profit Margin — margin kotor
- Revenue CAGR — pertumbuhan pendapatan
- Net Income CAGR — pertumbuhan laba
- FCF CAGR — pertumbuhan free cash flow

**Valuation Score** — Seberapa murah harganya?
- PER (Price to Earnings) — harga vs laba
- PBV (Price to Book) — harga vs nilai buku
- EV/EBITDA — nilai perusahaan vs laba sebelum pajak
- PEG — PER dibagi pertumbuhan

**Risk Score** — Seberapa aman investasinya?
- DER (Debt to Equity) — rasio utang
- Beta — volatilitas relatif terhadap pasar
- Current Ratio — kemampuan bayar utang jangka pendek

### 7.2 Cara Normalisasi

Setiap metrik dinormalisasi ke 0–100 dengan fungsi `_norm(v, lo, hi)`:
- Nilai terbaik (hi) → 100
- Nilai terburuk (lo) → 0
- Di luar range: clamp ke 0 atau 100

Contoh: ROE 15% → `_norm(0.15, 0.0, 0.30)` → 50

### 7.3 Rekomendasi Otomatis

```
Composite = 35% Quality + 35% Valuation + 30% Risk

Strong Buy  → Composite ≥ 75 DAN Valuation ≥ 60
Buy         → Composite ≥ 60 DAN Valuation ≥ 45
Hold        → Composite ≥ 45
Avoid       → Composite < 45
```

---

## 8. Model Valuasi

### 8.1 DCF (Discounted Cash Flow)
Model utama. Proyeksi FCF ke depan lalu didiskon ke nilai sekarang menggunakan WACC.

### 8.2 PBV (Price-to-Book Justified)
Cocok untuk bank. Menghitung PBV wajar berdasarkan ROE, biaya ekuitas, dan growth rate.
```
Justified PBV = (ROE - g) / (COE - g)
Intrinsic Value = Justified PBV × Book Value per Share
```

### 8.3 DDM (Gordon Growth / Dividend Discount Model)
Untuk saham yang rutin bagi dividen.
```
Intrinsic Value = D1 / (COE - g)
D1 = Last Dividend × (1 + g)
```

### 8.4 ROE Sustainable Growth
Menghitung nilai berdasarkan pertumbuhan sustainable dari ROE dan retention ratio.
```
g_sustainable = ROE × Retention Ratio
Intrinsic Value = EPS × (1 + g) / (COE - g)
```

---

## 9. Deployment

### 9.1 Development (Local)
```bash
cd claude-test-stock-check-a1
uv run stock-checker-web
# → Server berjalan di http://localhost:5000
```

### 9.2 Produksi (via Cloudflare Tunnel)
```bash
# Terminal 1: jalankan server
uv run stock-checker-web

# Terminal 2: buka tunnel ke internet
cloudflared tunnel run stock-checker
# → Publik di https://stock.zuhdi.id
```

### 9.3 Alur Akses dari Internet

```
User Internet
    │ HTTPS
    ▼
Cloudflare Edge (CDN)
    │
    ▼ encrypted tunnel
cloudflared (daemon di PC)
    │ localhost
    ▼
Flask server :5000
```

Semua traffic lewat Cloudflare, PC tidak perlu punya IP publik atau buka port di router.

---

## 10. Ringkasan Koneksi Antar Komponen

```
                    ┌─────────────┐
                    │   Browser   │
                    │  (app.js)   │
                    └──────┬──────┘
                           │ HTTP/JSON
                    ┌──────▼──────┐
                    │  Flask App  │
                    │  (app.py)   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼─────┐ ┌────▼────┐ ┌────▼──────┐
       │  Routes/   │ │Services │ │Calculations│
       │  Blueprints│ │(logic)  │ │(formulas) │
       └────────────┘ └────┬────┘ └────────────┘
                           │
              ┌────────────┼────────────┐
              │                         │
       ┌──────▼──────┐         ┌────────▼────────┐
       │  SQLite DB  │         │  Yahoo Finance   │
       │  (alpha.db) │         │  (via yfinance)  │
       │  - watchlist│         │  - harga saham   │
       │  - notes    │         │  - lapkeu        │
       │  - dll      │         │  - info perus.   │
       └─────────────┘         └─────────────────┘
```

---

*Dokumen ini dibuat otomatis pada 2026-02-19 berdasarkan kode sumber di repositori ini.*
