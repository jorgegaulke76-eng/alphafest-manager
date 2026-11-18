"""HF65.24.26 — página de orçamento corporativo sem cadastro ou armazenamento de dados pessoais."""
from __future__ import annotations
import html
import re


def _numero(empresa):
    n = re.sub(r'\D', '', str((empresa or {}).get('whatsapp_catalogo') or (empresa or {}).get('celular') or ''))
    return ('55' + n if n and not n.startswith('55') else n)


def inject_corporate_home(pagina: str) -> str:
    if 'id="corporativo-alphafest"' in pagina:
        return pagina
    bloco = '''<style id="hf652426-corp-style">
    #corporativo-alphafest{background:linear-gradient(120deg,#eef8ff,#fff);padding:36px 20px;color:#163759}
    #corporativo-alphafest .corp-in{max-width:1120px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap}
    #corporativo-alphafest h2{font-size:clamp(23px,3vw,32px);margin:6px 0 10px}
    #corporativo-alphafest p{max-width:650px;margin:0;color:#42617a;line-height:1.55}
    #corporativo-alphafest a{background:#0b79cf;color:white;text-decoration:none;font-weight:700;padding:13px 21px;border-radius:12px;white-space:nowrap}
    </style><section id="corporativo-alphafest" aria-label="Brindes personalizados para empresas"><div class="corp-in"><div><span style="color:#1166a8;font-weight:800">ALPHAFEST PARA EMPRESAS</span><h2>Brindes corporativos com a sua marca</h2><p>Presentes para colaboradores, clientes, eventos e confraternizações. Conte sua ideia, quantidade e prazo para receber um orçamento personalizado.</p></div><a href="/empresas/">Solicitar orçamento empresarial</a></div></section>'''
    pos=pagina.find('<main class="main" id="produtos">')
    if pos < 0:
        pos=pagina.find('</main>')
    if pos < 0:
        pos=pagina.find('</body>')
    if pos >= 0:
        pagina=pagina[:pos]+bloco+pagina[pos:]
    nav_match=re.search(r'(<nav class="site-nav"[^>]*>\s*<div class="site-nav-in"[^>]*>)(.*?)(</div>\s*</nav>)', pagina, flags=re.S)
    if nav_match and 'href="/empresas/"' not in nav_match.group(2):
        pagina=pagina[:nav_match.start(3)]+'<a href="/empresas/">Para Empresas</a>'+pagina[nav_match.start(3):]
    return pagina


def corporate_page(empresa: dict) -> str:
    telefone=_numero(empresa)
    safe_phone=html.escape(telefone,quote=True)
    # Form only builds a wa.me link on user click. No site-side storage or network submission.
    return '''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Brindes corporativos em Itatiba | AlphaFest</title><meta name="description" content="Solicite orçamento de brindes e presentes personalizados para empresas em Itatiba. Canecas, kits, chaveiros, impressão 3D e papelaria."><link rel="canonical" href="https://alphafest.com.br/empresas/"><meta name="theme-color" content="#0796e8"><style>
    *{box-sizing:border-box}body{margin:0;font-family:system-ui,Arial,sans-serif;color:#143455;background:#f3f9ff;line-height:1.5}header{background:linear-gradient(110deg,#0877cc,#08b1e4);color:#fff;padding:24px max(20px,calc((100% - 1120px)/2))}header a{color:#fff}header h1{font-size:clamp(25px,4vw,42px);margin:13px 0 4px}header p{max-width:700px;margin:0}main{max-width:1120px;margin:28px auto;padding:0 18px}.layout{display:grid;grid-template-columns:1fr 1.1fr;gap:24px;align-items:start}section,.panel{background:#fff;border:1px solid #dceafb;border-radius:18px;padding:24px;box-shadow:0 5px 22px #17466f0b}h2{margin:0 0 15px;color:#0863a7}ul{padding-left:22px}li{margin-bottom:12px}.note{color:#53718a;font-size:14px}label{display:block;font-weight:700;margin:14px 0 5px}input,select,textarea{width:100%;padding:12px;border:1px solid #b8d3ea;border-radius:9px;font:inherit;background:#fff;color:#183c5e}textarea{resize:vertical}button{width:100%;background:#16bd60;color:#fff;padding:15px;border:0;border-radius:11px;font-weight:800;font-size:16px;cursor:pointer;margin-top:20px}button:hover{background:#099e4b}.tiny{font-size:12px;color:#5b7188}footer{text-align:center;padding:22px;color:#426482}@media(max-width:760px){.layout{grid-template-columns:1fr}section,.panel{padding:18px}}
    </style></head><body><header><a href="/">← Voltar ao site AlphaFest</a><h1>Brindes corporativos AlphaFest</h1><p>Personalizados para equipes, clientes, fornecedores, eventos e confraternizações. Orçamento feito sob medida para a sua empresa.</p></header><main><div class="layout"><section><h2>Ideias para sua empresa</h2><ul><li><strong>Canecas e copos:</strong> lembranças para equipes e clientes</li><li><strong>Chaveiros e brindes em 3D:</strong> formatos personalizados</li><li><strong>Etiquetas, adesivos e papelaria:</strong> identidade visual da sua marca</li><li><strong>Kits de fim de ano:</strong> combinações conforme quantidade e orçamento</li><li><strong>Itens para eventos:</strong> crachás, cordões e presentes promocionais</li></ul><p class="note">Valores e prazos dependem da arte, técnica, quantidade, materiais e agenda de produção. O orçamento não representa uma compra.</p><a href="/#produtos">Conhecer os produtos do catálogo</a></section><div class="panel"><h2>Solicitar orçamento</h2><p class="note">Preencha os detalhes e revise a mensagem no WhatsApp antes de enviar.</p><form id="corp-form"><label for="corp-item">O que deseja personalizar?</label><select id="corp-item" required><option value="">Selecione uma opção</option><option>Canecas e copos</option><option>Kits corporativos</option><option>Chaveiros e impressão 3D</option><option>Crachás e cordões</option><option>Adesivos, etiquetas e papelaria</option><option>Outros personalizados</option></select><label for="corp-qtd">Quantidade aproximada</label><input id="corp-qtd" type="number" min="1" max="100000" step="1" placeholder="Ex.: 30" required><label for="corp-faixa">Faixa de orçamento (opcional)</label><select id="corp-faixa"><option value="">Prefiro conversar</option><option>Até R$ 500</option><option>R$ 500 a R$ 1.000</option><option>R$ 1.000 a R$ 2.500</option><option>Acima de R$ 2.500</option></select><label for="corp-data">Data desejada (opcional)</label><input id="corp-data" type="date"><label for="corp-detalhes">Cores, personalização e detalhes</label><textarea id="corp-detalhes" rows="4" maxlength="1500" placeholder="Ex.: aplicar nossa logo nas canecas..."></textarea><button type="submit">Solicitar pelo WhatsApp</button><p class="tiny">Você será direcionado ao WhatsApp e poderá revisar a mensagem. Nenhum dado é armazenado neste formulário.</p></form></div></div></main><footer>AlphaFest · Estamos presentes em cada presente!</footer><script>
    (function(){const form=document.getElementById('corp-form');form.addEventListener('submit',function(e){e.preventDefault();if(!form.reportValidity())return;const v=id=>document.getElementById(id).value.trim();const linhas=['Olá, AlphaFest! Gostaria de um orçamento empresarial.','Produto: '+v('corp-item'),'Quantidade aproximada: '+v('corp-qtd')];if(v('corp-faixa'))linhas.push('Orçamento pretendido: '+v('corp-faixa'));if(v('corp-data')){let d=v('corp-data').split('-');linhas.push('Data desejada: '+d.reverse().join('/'));}if(v('corp-detalhes'))linhas.push('Detalhes: '+v('corp-detalhes'));linhas.push('Podem confirmar as opções, valores e prazos?');const tel='''+repr(telefone)+''';if(!tel){alert('WhatsApp indisponível. Entre em contato pelo site.');return;}window.open('https://wa.me/'+tel+'?text='+encodeURIComponent(linhas.join('\\n')),'_blank','noopener,noreferrer');});})();
    </script></body></html>'''
