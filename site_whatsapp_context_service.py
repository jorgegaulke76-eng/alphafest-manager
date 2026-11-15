"""HF65.24.11 — contexto de navegação comercial enviado na mensagem WhatsApp.

Não identifica o visitante; mantém interesses mínimos somente durante a aba/sessão.
O cliente visualiza e confirma a mensagem antes de enviá-la pelo WhatsApp.
"""
from __future__ import annotations


_SCRIPT = r'''<script id="af-whatsapp-context-hf652411">
(function(){
  'use strict';
  if(window.__afWaContextInstalled) return;
  window.__afWaContextInstalled=true;
  const KEY='af_whatsapp_interest_v1';
  const TTL=45*60*1000;
  const MAX_ITEMS=8;
  function clean(raw,max=85){
    return String(raw||'').replace(/[\r\n\t]+/g,' ').replace(/\s+/g,' ').trim().slice(0,max);
  }
  function load(){
    try{
      const data=JSON.parse(sessionStorage.getItem(KEY)||'{}');
      if(!Array.isArray(data.items) || !Number.isFinite(data.updated) || Date.now()-data.updated>TTL) return [];
      return data.items.filter(x=>x&&typeof x.label==='string'&&typeof x.kind==='string').slice(-MAX_ITEMS);
    }catch(e){return [];}
  }
  function save(items){
    try{sessionStorage.setItem(KEY,JSON.stringify({updated:Date.now(),items:items.slice(-MAX_ITEMS)}));}catch(e){}
  }
  function remember(kind,value){
    const label=clean(value);
    if(!label || label.length<3 || /^(todos|todas|produto|produtos|alpha\s?fest|início|buscar)$/i.test(label))return;
    let items=load().filter(x=>!(x.kind===kind && x.label.toLowerCase()===label.toLowerCase()));
    items.push({kind,label});save(items);
  }
  // Páginas editoriais (sem URLs com parâmetros, nomes de cliente ou informações pessoais).
  const path=location.pathname.replace(/\/+$/,'/')||'/';
  const heading=document.querySelector('main article h1,main h1');
  if(path.startsWith('/dicas/') && path!=='/dicas/' && heading){remember('Dica',heading.textContent);}
  function productName(el){
    if(!el)return '';
    return clean(el.getAttribute('data-detail-name')||el.getAttribute('data-hf50-product')||
      el.getAttribute('data-gallery-title')||el.querySelector('h2,h3,[data-product-name]')?.textContent||'',85);
  }
  function isWhatsapp(a){
    if(!a || !a.href)return false;
    try{const u=new URL(a.href,location.href);const host=u.hostname.toLowerCase();
      return (host==='wa.me'||host==='api.whatsapp.com'||host==='web.whatsapp.com'||host==='www.whatsapp.com') &&
        (host==='wa.me'||u.pathname.startsWith('/send'));
    }catch(e){return false;}
  }
  function formatMessage(anchor){
    let url;
    try{url=new URL(anchor.href,location.href);}catch(e){return;}
    // Excluir número do telefone e parâmetros extras da lista de interesses.
    let initial=clean((url.searchParams.get('text')||''),340);
    const gallery=anchor.closest('.gallery-card');
    const prod=anchor.closest('.product-card,[data-hf50-product],.product-related-card');
    const modal=document.getElementById('product-detail-name');
    const focus=gallery?productName(gallery):(prod?productName(prod):(modal && modal.textContent?clean(modal.textContent):''));
    if(focus)remember('Produto',focus);
    const all=load();
    const products=all.filter(x=>x.kind==='Produto').slice(-4).reverse();
    const categories=all.filter(x=>x.kind==='Categoria').slice(-2).reverse();
    const articles=all.filter(x=>x.kind==='Dica').slice(-2).reverse();
    const lines=[];
    if(products.length) lines.push('🎁 Produtos vistos: '+products.map(x=>x.label).join(' • '));
    if(categories.length)lines.push('🛍️ Categorias: '+categories.map(x=>x.label).join(' • '));
    if(articles.length)lines.push('📖 Dicas consultadas: '+articles.map(x=>x.label).join(' • '));
    if(!lines.length){
      const page=clean(document.querySelector('main h1')?.textContent||document.title.replace(/\s*\|.*$/,''),75);
      if(page && path!=='/')lines.push('📍 Página consultada: '+page);
    }
    if(!lines.length)return;
    // Mensagem visível e editável pelo visitante: nenhum envio automático.
    const preamble='\n\n📌 Meu interesse no site AlphaFest:\n';
    const footer='\n(Informações da minha visita; posso editar antes de enviar.)';
    const suffix=lines.join('\n');
    let max=850-initial.length-preamble.length-footer.length;
    if(max<110){initial=initial.slice(0,240);max=850-initial.length-preamble.length-footer.length;}
    url.searchParams.set('text',(initial+preamble+suffix.slice(0,max)+footer).trim());
    anchor.href=url.toString();
  }
  document.addEventListener('click',function(event){
    const target=event.target instanceof Element?event.target:null;
    if(!target)return;
    const a=target.closest('a[href]');
    if(a && isWhatsapp(a)){
      // Atualiza href antes da navegação padrão, inclusive target=_blank.
      formatMessage(a);return;
    }
    const product=target.closest('.product-card,[data-hf50-product],.product-related-card');
    if(product)remember('Produto',productName(product)||clean(product.textContent));
    const gallery=target.closest('.gallery-photo-open,.gallery-card');
    if(gallery)remember('Produto',gallery.getAttribute('data-gallery-title')||productName(gallery)||gallery.querySelector('img')?.alt);
    const cat=target.closest('[data-cat],[data-label],.category-filter');
    if(cat)remember('Categoria',cat.getAttribute('data-label')||cat.textContent);
    const hint=target.closest('a[href^="/dicas/"],a[href*="/dicas/"]');
    if(hint && !isWhatsapp(hint)){const card=hint.closest('.alpha-dicas-card,.card');if(card)remember('Dica',card.querySelector('h2,h3')?.textContent);}
  },true);
})();
</script>'''


def inject_whatsapp_context(html_page: str) -> str:
    """Instrumenta página HTML pública sem acessar Supabase nem alterar CSS/layout."""
    page = str(html_page or "")
    if not page or 'id="af-whatsapp-context-hf652411"' in page:
        return page
    if '</body>' in page:
        return page.replace('</body>', _SCRIPT + '</body>', 1)
    return page + _SCRIPT
