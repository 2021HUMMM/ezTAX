# TaxGate — Mesin Pencari Peraturan Pajak Indonesia

TaxGate adalah aplikasi pencarian semantik berbasis AI untuk peraturan perpajakan Indonesia. Berbeda dari pencarian biasa yang mencocokkan kata per kata, TaxGate memahami *makna* dari query — sehingga bisa menemukan dokumen yang relevan meskipun pengguna menggunakan bahasa sehari-hari, singkatan, atau sedikit typo.

---

## Fitur Utama

- **Semantic Search** — Pencarian berbasis makna menggunakan vector embedding OpenAI `text-embedding-3-small`
- **AI Query Enhancer** — Query informal (misal: "pajak freelancer") diterjemahkan ke istilah formal perpajakan menggunakan GPT-4o-mini sebelum dicari
- **Pencarian Nomor Dokumen** — Jika query mengandung nomor peraturan spesifik (misal: `112/KMK.03/2001`, `PER-61/PJ./2009`, `7 TAHUN 1983`), sistem langsung mencari via metadata filter — tidak bergantung pada semantic similarity
- **Filter Kategori & Jenis Dokumen** — Bisa filter berdasarkan kategori peraturan (PPh, PPN, PBB, dll.) dan jenis dokumen (Undang-Undang, PMK, Keputusan Dirjen Pajak, dll.)
- **Title Boosting** — Dokumen yang judulnya cocok dengan query mendapat skor tambahan
- **Deduplication** — Satu dokumen hanya muncul sekali di hasil, meskipun memiliki banyak chunk yang relevan

---

## Data

- **Sumber**: [pajak.go.id](https://pajak.go.id)
- **Jumlah dokumen**: 3.201 peraturan pajak
- **Jenis dokumen**: Undang-Undang, Peraturan Pemerintah, PMK, Keputusan Menteri Keuangan, Peraturan Dirjen Pajak, dan lainnya
- **Format penyimpanan**: Setiap dokumen dipotong menjadi chunks (~1.000 karakter dengan overlap 200 karakter), lalu di-embed dan disimpan di ChromaDB

---

## Tech Stack

| Komponen | Teknologi |
|---|---|
| Web Framework | Django 6 |
| Vector Database | ChromaDB (lokal) |
| Embedding Model | OpenAI `text-embedding-3-small` |
| AI Query Expansion | OpenAI `gpt-4o-mini` |
| Text Splitting | LangChain `RecursiveCharacterTextSplitter` |

---

## Alur Pencarian

```
Query user
   │
   ▼
[Opsional] AI Query Enhancer (GPT-4o-mini)
   │         → Skip jika query sudah formal (ada nomor/tahun/akronim resmi)
   │
   ▼
Deteksi nomor dokumen di query
   │
   ├─ Ada nomor? → Fetch langsung via metadata filter (exact match)
   │               Coba format dengan/tanpa spasi: KEP-131 & KEP - 131
   │
   ├─ Semantic Search → ChromaDB similarity search (top 20-60 kandidat)
   │
   ▼
Gabungkan kandidat (nomor lookup + semantic search)
   │
   ▼
Scoring:
   ├─ Base: cosine similarity score (0–1)
   ├─ +0.4 title boost (proporsional kata query yang ada di judul)
   ├─ +0.3 jenis dokumen boost (jika query menyebut jenis tertentu)
   └─ +0.5 exact nomor match bonus
   │
   ▼
Deduplikasi per dokumen → ambil chunk dengan skor tertinggi
   │
   ▼
Tampilkan hasil terurut berdasarkan skor
```

---

## Struktur Folder

```
taxgate_django/
├── manage.py
├── requirements.txt
├── DESCRIPTION.md
├── .env                          ← berisi API_KEY (tidak di-commit)
├── chroma_db_pajak_openai/       ← vector database (ChromaDB)
├── taxgate_django/
│   ├── settings.py               ← konfigurasi Django + CHROMA_DB_PATH
│   ├── urls.py
│   └── wsgi.py
└── search/
    ├── engine.py                 ← inti logika pencarian
    ├── views.py                  ← index view + /api/search/ endpoint
    ├── urls.py
    ├── apps.py                   ← inisialisasi ChromaDB saat server start
    └── templates/search/
        └── index.html            ← UI pencarian
```

### File Pendukung (di luar folder Django)

```
├── bangun_otak_ai_openai.py   ← script untuk rebuild vector DB
├── get_links_pajak.py         ← scraping daftar link dari pajak.go.id
├── get_data_from_links.py     ← scraping konten dari setiap link
├── sanitize_json_data.py      ← cleaning & deduplication data
└── database_pajak_sanitized.json  ← 3.201 dokumen hasil scraping
```

---

## Setup & Menjalankan

### Prasyarat
- Python 3.10+
- OpenAI API key

### Langkah

```bash
cd taxgate_django

# Buat dan aktifkan virtual environment
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Buat file .env
echo "API_KEY=sk-..." > .env

# Jalankan server
python manage.py runserver
```

Akses di: `http://127.0.0.1:8000`

---

## Biaya Operasional

| Komponen | Biaya |
|---|---|
| Rebuild vector DB (sekali jalan, 3.201 dokumen) | ~$0.06 |
| Per query embedding | ~$0.000001 (negligible) |
| Per query AI expand (GPT-4o-mini) | ~$0.00007 |

Vector DB cukup dibangun sekali. Setelah itu hanya ada biaya API per query jika AI Query Enhancer diaktifkan.

---

## Deployment ke VPS

Folder `taxgate_django/` sudah self-contained (ChromaDB sudah di dalam). Cukup:

1. Upload folder ke VPS (rsync/scp)
2. Buat file `.env` dengan `API_KEY`
3. Install dependencies & jalankan

Tidak memerlukan GPU.
