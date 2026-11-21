"""HF65.24.52 - smoke tests sem rede, com scripts JS reais extraidos dos modulos.

Nao acessa Supabase, WhatsApp ou clientes.
"""
from __future__ import annotations

import ast
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js indisponivel")


def _run_node(js: str, source: str) -> None:
    completed = subprocess.run(
        ["node", "-e", js, source],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, (completed.stdout + "\n" + completed.stderr)


def _vitrine_script() -> str:
    tree = ast.parse((ROOT / "site_vitrine_service.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "product_detail_script" for t in node.targets
        ):
            return re.sub(r"^<script>\s*|\s*</script>$", "", ast.literal_eval(node.value))
    raise AssertionError("Script da ficha nao localizado")


def test_link_direto_abre_ficha_e_slug_invalido_nao_abre():
    js = r"""
const vm=require('vm');
const code=process.argv[1];
function render(search){
  const noop=()=>{};
  const make=()=>({dataset:{},hidden:true,textContent:'',classList:{add:noop,remove:noop},
    addEventListener:noop,setAttribute:noop,focus:noop,removeAttribute:noop});
  const names=['product-detail-modal','product-detail-name','product-detail-description',
    'product-detail-tax','product-detail-price','product-detail-image',
    'product-detail-placeholder','product-detail-whatsapp','product-detail-gallery',
    'product-related','product-related-grid'];
  const nodes=Object.fromEntries(names.map(n=>[n,make()]));
  nodes['product-detail-modal'].querySelector=()=>({focus:noop});
  nodes['product-detail-modal'].querySelectorAll=()=>[];
  const card=make();
  card.dataset={product:'bubble-personalizado',productAliases:'bubble-antigo',detailName:'Bubble personalizado',
    detailDescription:'Produto AlphaFest',detailWhatsapp:'https://wa.me/5511999999999',
    detailGallery:'0',detailCategory:'Baloes',detailSubcategory:''};
  const document={getElementById:id=>nodes[id]||null,
    querySelectorAll:sel=>sel.includes('.product-card[data-detail-name]')?[card]:[],
    addEventListener:noop,body:{classList:{add:noop,remove:noop}}};
  const window={location:{search}};
  vm.runInNewContext(code,{document,window,URLSearchParams});
  return nodes;
}
let ok=render('?produto=bubble-personalizado&utm_campaign=natal-2026');
if(ok['product-detail-modal'].hidden!==false) throw Error('Ficha nao abriu');
if(ok['product-detail-name'].textContent!=='Bubble personalizado') throw Error('Produto incorreto');
if(ok['product-detail-whatsapp'].href!=='https://wa.me/5511999999999') throw Error('Link WhatsApp alterado');
let legacy=render('?produto=bubble-antigo&utm_campaign=natal-2026');
if(legacy['product-detail-modal'].hidden!==false) throw Error('Alias historico nao abriu ficha');
if(legacy['product-detail-name'].textContent!=='Bubble personalizado') throw Error('Alias apontou para ficha errada');
let bad=render('?produto=outro-item');
if(bad['product-detail-modal'].hidden!==true) throw Error('Produto inexistente abriu');
let invalid=render('?produto=%3Cscript%3E');
if(invalid['product-detail-modal'].hidden!==true) throw Error('Slug invalido abriu');
"""
    _run_node(js, _vitrine_script())


def test_utm_persiste_em_sessao_e_clique_whatsapp_nao_duplica(monkeypatch):
    import site_metrics_service as metrics

    monkeypatch.setattr(metrics, "tracking_available", lambda: True)
    monkeypatch.setattr(
        metrics, "public_config",
        lambda: {"url": "https://example.supabase.co", "key": "sb_publishable_test"},
    )
    page = metrics.inject_tracking("<html><body></body></html>")
    found = re.search(r'<script id="alphafest-site-metrics">(.*?)</script>', page, re.S)
    assert found, "Rastreador nao foi injetado"
    js = r"""
const vm=require('vm');
const code=process.argv[1];
const makeStorage=()=>{
 const values=new Map();
 return {getItem:k=>values.has(k)?values.get(k):null,setItem:(k,v)=>values.set(k,String(v))};
};
const sessionStorage=makeStorage(),localStorage=makeStorage();
let seq=0;
function run(search, opts={}){
  const posts=[], handlers={};
  const card={dataset:{product:'bubble-personalizado',productAliases:'bubble-antigo',detailName:'Bubble personalizado'}};
  const modalName={textContent:'Bubble personalizado'};
  const document={
    referrer:opts.referrer||'',
    querySelectorAll:sel=>sel.includes('.product-card[data-product]')?[card]:[],
    getElementById:id=>id==='product-detail-name'?modalName:null,
    addEventListener:(name,fn)=>{handlers['doc:'+name]=fn;}
  };
  const window={addEventListener:(name,fn)=>{handlers['win:'+name]=fn;}};
  const location={protocol:'https:',pathname:opts.pathname||'/',hash:opts.hash||'',search};
  const fetch=(url,opts)=>{
    if(opts&&opts.method==='POST') posts.push(JSON.parse(opts.body));
    return Promise.resolve({ok:false,json:()=>Promise.resolve({})});
  };
  const context={window,location,document,sessionStorage,localStorage,
    navigator:{userAgent:'Chrome/120'},screen:{width:1200,height:800},
    crypto:{randomUUID:()=>String(++seq)},fetch,URL,URLSearchParams,
    setTimeout,clearTimeout};
  vm.runInNewContext(code,context);
  return {posts,handlers};
}
let privacy=run('?utm_source=instagram&utm_campaign=campanha-privada&telefone=11999998888',{
  pathname:'/novidades/',hash:'#contato=ana',referrer:'https://instagram.com/p/abc?email=ana@example.org'
});
const safe=privacy.posts[0];
if(safe.page_path!=='/novidades/' || safe.entry_path!=='/novidades/')
  throw Error('Caminhos continuam expondo query string ou fragmento');
if(safe.referrer!=='https://instagram.com/p/abc')
  throw Error('Origem da visita continua expondo parametros pessoais');
if(JSON.stringify(safe).includes('ana@example.org') || JSON.stringify(safe).includes('11999998888'))
  throw Error('Dado pessoal nao relacionado a campanha foi registrado');
let a=run('?produto=bubble-personalizado&utm_source=instagram&utm_medium=stories&utm_campaign=natal-2026');
const type=(r,t)=>r.posts.filter(x=>x.event_type===t);
if(type(a,'page_view').length!==1 || type(a,'product_open').length!==1)
  throw Error('Abertura direta nao gera um evento por tipo');
if(type(a,'product_open')[0].product_name!=='Bubble personalizado')
  throw Error('Produto diferente do anuncio');
const anchor={
 closest:(selector)=>{
   if(selector==='a,button,.product-card,.product-related-card') return anchor;
   if(selector.includes('a[href*=')) return anchor;
   return null;
 }
};
a.handlers['doc:click']({target:anchor});
if(type(a,'whatsapp_click').length!==1)
  throw Error('Clique WhatsApp nao contado uma unica vez');
if(type(a,'whatsapp_click')[0].utm_campaign!=='natal-2026')
  throw Error('WhatsApp perdeu campanha');
let b=run('?filtro=promocoes');
if(type(b,'page_view').length!==1)
  throw Error('Nova navegacao sem acesso registrado');
const second=type(b,'page_view')[0];
if(second.utm_campaign!=='natal-2026' || second.utm_source!=='instagram')
  throw Error('Campanha perdida na navegacao interna');
let legacy=run('?produto=bubble-antigo&utm_source=instagram&utm_medium=stories&utm_campaign=historico');
if(type(legacy,'product_open').length!==1 || type(legacy,'product_open')[0].product_name!=='Bubble personalizado')
  throw Error('Metrica de alias historico ausente ou duplicada');
let cart=run('');
cart.handlers['win:alphafest:metric']({
  detail:{type:'whatsapp_click',product:'Orcamento com 2 produtos',context:'carrinho'}
});
if(type(cart,'whatsapp_click').length!==1 || type(cart,'whatsapp_click')[0].event_context!=='carrinho')
  throw Error('Carrinho nao registrou um clique separado');
"""
    _run_node(js, found.group(1))
