from datetime import date
from io import BytesIO
from zipfile import ZipFile
from site_posts_service import normalize,published,inject_home,archive_pages
from site_production_service import gerar_pacote_producao


def post(i,status='publicado',expiry=''):
    return {'id':str(i),'title':f'Arte {i}','description':'Produto personalizado','category':'Natal','image_data_uri':'data:image/png;base64,aGVsbG8=','status':status,'created_at':'2026-11-18','featured':False,'expires_at':expiry}


def test_posts_publicacao_segura():
    entries=[post(1),post(2,status='rascunho'),post(3,expiry='2026-11-01')]
    assert len(published(entries,today=date(2026,11,18)))==1
    html=inject_home('<html><head></head><body><footer class="footer"></footer></body></html>',entries,'11972949533')
    assert 'id="novidades-alphafest"' in html
    assert 'Arte 1' in html and 'Arte 2' not in html and 'Arte 3' not in html
    assert 'object-fit:contain' in html
    archive=archive_pages(entries,'11972949533')
    assert 'novidades/index.html' in archive
    assert 'Arte 1' in archive['novidades/index.html'] and 'Arte 2' not in archive['novidades/index.html']


def test_posts_paginacao():
    archive=archive_pages([post(i) for i in range(50)], '11972949533')
    assert len(archive)==3
    assert 'novidades/pagina-2/index.html' in archive
    assert 'novidades/pagina-3/index.html' in archive
    assert archive['novidades/index.html'].count('class="afposts-card"')==24
    assert archive['novidades/pagina-3/index.html'].count('class="afposts-card"')==2


def test_posts_arquivo_pwa():
    z=ZipFile(BytesIO(gerar_pacote_producao('<html><head></head><body>AlphaFest</body></html>',posts_content=[post(1)],dicas_content=[])))
    assert 'novidades/index.html' in z.namelist()
    assert b'manifest.webmanifest' in z.read('novidades/index.html')
    assert 'novidades/index.html' in z.read('sitemap.xml').decode() or 'novidades/' in z.read('sitemap.xml').decode()
