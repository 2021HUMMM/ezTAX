import os
import re
from openai import OpenAI
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

openai_client = OpenAI(api_key=os.getenv("API_KEY"))

JUMLAH_KANDIDAT_BASE = 20
JUMLAH_KANDIDAT_FILTER = 60

DAFTAR_KATEGORI = [
    "- Apa saja -",
    "BM - Bea Meterai",
    "BPHTB - Bea Perolehan Hak atas Tanah dan Bangunan",
    "KUP - Ketentuan Umum Perpajakan",
    "Lainnya",
    "PBB - Pajak Bumi dan Bangunan",
    "PPh - Pajak Penghasilan",
    "PPN - Pajak Pertambahan Nilai",
]

DAFTAR_JENIS_DOKUMEN = [
    "- Apa saja -",
    "Instruksi Dirjen Pajak",
    "Instruksi Menteri Keuangan",
    "Instruksi Presiden",
    "Keputusan Bersama Dirjen",
    "Keputusan Bersama Menteri",
    "Keputusan Dirjen Bea dan Cukai",
    "Keputusan Dirjen Pajak",
    "Keputusan Dirjen Perbendaharaan",
    "Keputusan Ketua Pengadian Pajak",
    "Keputusan Menteri Dalam Negeri",
    "Keputusan Menteri Keuangan",
    "Keputusan Menteri Perindustrian",
    "Keputusan Menteri Tenaga Kerja",
    "Keputusan Presiden",
    "Nota Dinas Direktur Jenderal Pajak",
    "Pengumuman",
    "Peraturan Badan Koordinasi dan Penanaman Modal",
    "Peraturan Bersama Dirjen",
    "Peraturan Bersama Menteri",
    "Peraturan Daerah",
    "Peraturan Dirjen Pajak",
    "Peraturan Dirjen Perbendaharaan",
    "Peraturan Dirjen Perdagangan Luar Negeri",
    "Peraturan Lainnya",
    "Peraturan Menteri Keuangan",
    "Peraturan Menteri Perdagangan",
    "Peraturan Menteri Perindustrian",
    "Peraturan Pemerintah",
    "Peraturan Presiden",
    "Perpu",
    "Peraturan Menteri Dalam Negeri",
    "Surat Dirjen Anggaran",
    "Surat Dirjen Bea dan Cukai",
    "Surat Dirjen Perbendaharaan",
    "Undang-Undang",
    "Undang Dasar",
]

AKRONIM_PAJAK = {
    "spt": "Surat Pemberitahuan",
    "npwp": "Nomor Pokok Wajib Pajak",
    "ppn": "Pajak Pertambahan Nilai",
    "pph": "Pajak Penghasilan",
    "pkp": "Pengusaha Kena Pajak",
    "bkp": "Barang Kena Pajak",
    "jkp": "Jasa Kena Pajak",
    "skp": "Surat Ketetapan Pajak",
    "skpkb": "Surat Ketetapan Pajak Kurang Bayar",
    "skplb": "Surat Ketetapan Pajak Lebih Bayar",
    "stp": "Surat Tagihan Pajak",
    "kup": "Ketentuan Umum Perpajakan",
    "pbb": "Pajak Bumi dan Bangunan",
    "bphtb": "Bea Perolehan Hak atas Tanah dan Bangunan",
    "bm": "Bea Meterai",
    "dtp": "Ditanggung Pemerintah",
    "pmk": "Peraturan Menteri Keuangan",
    "pp": "Peraturan Pemerintah",
    "uu": "Undang-Undang",
    "perdirjen": "Peraturan Direktur Jenderal Pajak",
    "djp": "Direktorat Jenderal Pajak",
}

JENIS_BOOST = {
    "undang": "undang-undang",
    "peraturan pemerintah": "peraturan pemerintah",
    "pmk": "peraturan menteri keuangan",
    "perdirjen": "peraturan dirjen pajak",
    "keputusan menteri": "keputusan menteri keuangan",
}

POLA_FORMAL = re.compile(
    r'\b(nomor\s+\d+|tahun\s+\d{4}|\d+\s+tahun\s+\d{4}|pmk|per-|kep-|pp\s+no|uu\s+no)\b',
    re.IGNORECASE
)

POLA_NOMOR = re.compile(
    r'([a-z]+-\d+(?:/[\w\.]+)+/\d{4}|\d+(?:/[\w\.]+)+/\d{4}|\d+\s+tahun\s+\d{4})'
)

db_vektor = None


def normalisasi_nomor(s):
    """Hapus spasi di sekitar dash: 'KEP - 131' → 'KEP-131'"""
    return re.sub(r'\s*-\s*', '-', s)


def muat_database():
    global db_vektor
    print("🤖 Menghubungkan ke Qdrant Cloud...")
    model_embedding = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("API_KEY")
    )
    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_KEY"),
    )
    db_vektor = QdrantVectorStore(
        client=qdrant_client,
        collection_name="peraturan_pajak_openai",
        embedding=model_embedding,
        content_payload_key="page_content",
        metadata_payload_key="metadata",
    )
    print("✅ Database siap!")


def expand_query(query):
    if POLA_FORMAL.search(query):
        return query

    akronim_relevan = {k: v for k, v in AKRONIM_PAJAK.items() if k in query.lower().split()}
    konteks_akronim = ""
    if akronim_relevan:
        konteks_akronim = "Akronim yang WAJIB digunakan dengan benar:\n"
        konteks_akronim += "\n".join(f"- {k.upper()} = {v}" for k, v in akronim_relevan.items()) + "\n\n"

    prompt = (
        "Ubah query pencarian ini ke istilah formal perpajakan Indonesia. "
        "Balas HANYA dengan satu baris kata kunci pencarian, tanpa penjelasan, tanpa nomor, tanpa bullet point.\n\n"
        + konteks_akronim +
        "Contoh:\n"
        "Input: pajak freelancer\n"
        "Output: pajak penghasilan pekerjaan bebas tenaga ahli jasa profesional\n\n"
        "Input: pajak jual rumah\n"
        "Output: pajak penghasilan pengalihan hak atas tanah dan bangunan BPHTB\n\n"
        "Input: siapa yang bebas pajak\n"
        "Output: subjek pajak dikecualikan tidak kena pajak pengecualian objek pajak\n\n"
        "Input: apa saja yang kena ppn\n"
        "Output: barang kena pajak jasa kena pajak objek PPN\n\n"
        f"Input: {query}\n"
        "Output:"
    )
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Kamu adalah sistem pencarian peraturan perpajakan Indonesia. Tugasmu HANYA menerjemahkan query ke istilah resmi perpajakan Indonesia. Balas HANYA dengan satu baris kata kunci, tanpa penjelasan apapun. DILARANG menambahkan nomor peraturan atau tahun yang tidak ada di query asli."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=60,
        )
        expanded = resp.choices[0].message.content.strip().splitlines()[0].strip()
        if expanded:
            return expanded
    except Exception as e:
        print(f"⚠️ OpenAI expand gagal: {e}")
    return query


def cari_dokumen(query, jumlah_hasil, kategori, jenis_dokumen, pakai_ai):
    if not query.strip():
        return []

    jumlah_hasil = int(jumlah_hasil)
    query_expanded = expand_query(query) if pakai_ai else query

    where_filter = None
    if jenis_dokumen and jenis_dokumen != "- Apa saja -":
        where_filter = rest.Filter(must=[
            rest.FieldCondition(
                key="metadata.jenis_dokumen",
                match=rest.MatchValue(value=jenis_dokumen)
            )
        ])

    filter_kategori = None
    if kategori and kategori != "- Apa saja -":
        filter_kategori = kategori.split(" - ")[0]

    query_norm = normalisasi_nomor(query.lower())
    pola_nomor_awal = POLA_NOMOR.findall(query_norm)

    jumlah_kandidat = JUMLAH_KANDIDAT_FILTER if filter_kategori else JUMLAH_KANDIDAT_BASE

    kwargs = {"k": jumlah_kandidat}
    if where_filter:
        kwargs["filter"] = where_filter
    kandidat = db_vektor.similarity_search_with_relevance_scores(query_expanded, **kwargs)

    if pola_nomor_awal:
        nomor_sudah_ada = {normalisasi_nomor(doc.metadata.get("nomor_dokumen", "").upper()) for doc, _ in kandidat}
        for pola in pola_nomor_awal:
            nomor_target = normalisasi_nomor(pola.upper())
            if nomor_target not in nomor_sudah_ada:
                nomor_spasi = re.sub(r'-', ' - ', nomor_target, count=1)
                for variant in [nomor_target, nomor_spasi]:
                    try:
                        conditions = [
                            rest.FieldCondition(
                                key="metadata.nomor_dokumen",
                                match=rest.MatchValue(value=variant)
                            )
                        ]
                        if where_filter:
                            conditions.append(rest.FieldCondition(
                                key="metadata.jenis_dokumen",
                                match=rest.MatchValue(value=jenis_dokumen)
                            ))
                        f = rest.Filter(must=conditions)
                        hasil_nomor = db_vektor.similarity_search_with_relevance_scores(query_expanded, k=3, filter=f)
                        if hasil_nomor:
                            kandidat = hasil_nomor + kandidat
                            break
                    except Exception:
                        pass

    if filter_kategori:
        kandidat = [
            (doc, skor) for doc, skor in kandidat
            if filter_kategori in doc.metadata.get("kategori_peraturan", "")
        ]

    if not kandidat:
        return []

    query_lower = re.sub(r'[^\w\s]', '', query_expanded.lower())
    query_tokens = set(query_lower.split())
    pola_nomor = pola_nomor_awal

    query_jenis_boost = None
    for kata, jenis_target in JENIS_BOOST.items():
        if kata in query.lower():
            query_jenis_boost = jenis_target
            break

    skor_final = []
    for doc, skor_similarity in kandidat:
        judul = doc.metadata.get('judul', '').lower()
        nomor = doc.metadata.get('nomor_dokumen', '').lower()
        jenis = doc.metadata.get('jenis_dokumen', '').lower()
        gabungan = f"{jenis} {judul} {nomor}"

        cocok = sum(1 for t in query_tokens if t in gabungan)
        rasio_cocok = cocok / len(query_tokens) if query_tokens else 0
        bonus = rasio_cocok * 0.4

        if query_jenis_boost and query_jenis_boost in jenis:
            bonus += 0.3

        nomor_clean = re.sub(r'[^\w\s]', '', normalisasi_nomor(nomor))
        for pola in pola_nomor:
            pola_clean = re.sub(r'[^\w\s]', '', normalisasi_nomor(pola)).strip()
            if pola_clean and pola_clean in nomor_clean:
                bonus += 0.5
                break

        skor_final.append(skor_similarity + bonus)

    semua = sorted(zip(kandidat, skor_final), key=lambda x: x[1], reverse=True)

    terlihat = set()
    hasil = []
    for (doc, _), skor_total in semua:
        nomor_dok = doc.metadata.get("nomor_dokumen", "")
        judul_dok = doc.metadata.get("judul", "")
        kunci = (nomor_dok, judul_dok)
        if kunci not in terlihat:
            terlihat.add(kunci)
            konten = doc.page_content
            cuplikan = konten.split("\n\n", 1)[1] if "\n\n" in konten else konten
            cuplikan = cuplikan.replace('\n', ' ')
            if len(cuplikan) > 400:
                cuplikan = cuplikan[:400] + "..."

            if skor_total > 0.85:
                warna_skor = "#22c55e"
            elif skor_total > 0.6:
                warna_skor = "#eab308"
            else:
                warna_skor = "#ef4444"

            hasil.append({
                "judul": doc.metadata.get("judul", "Tanpa Judul"),
                "nomor": nomor_dok,
                "url": doc.metadata.get("url", "#"),
                "kategori": doc.metadata.get("kategori_peraturan", ""),
                "jenis": doc.metadata.get("jenis_dokumen", ""),
                "cuplikan": cuplikan,
                "skor": round(skor_total, 2),
                "warna_skor": warna_skor,
            })
        if len(hasil) >= jumlah_hasil:
            break

    return hasil
