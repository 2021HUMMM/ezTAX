import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from . import engine


def index(request):
    return render(request, 'search/index.html', {
        'daftar_kategori': engine.DAFTAR_KATEGORI,
        'daftar_jenis': engine.DAFTAR_JENIS_DOKUMEN,
    })


@csrf_exempt
@require_POST
def search_api(request):
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        jumlah = data.get('jumlah', 5)
        kategori = data.get('kategori', '- Apa saja -')
        jenis = data.get('jenis', '- Apa saja -')
        pakai_ai = data.get('pakai_ai', False)

        if not query:
            return JsonResponse({'results': [], 'error': 'Query kosong'})

        hasil = engine.cari_dokumen(query, jumlah, kategori, jenis, pakai_ai)
        return JsonResponse({'results': hasil})

    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)}, status=500)
