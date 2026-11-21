"""HF65.24.24 — Carrinho de solicitação de orçamento, apenas no navegador do visitante.

Não coleta dados pessoais nem envia pedidos automaticamente; usa o WhatsApp
público configurado no Manager. Preserva os CTAs individuais e os rastreadores.
"""
from __future__ import annotations
import html
import json
import re

CSS = r'''
#afquote-trigger{position:fixed;right:18px;bottom:18px;z-index:82;display:flex;align-items:center;gap:8px;background:#0479bd;color:white;border:2px solid white;border-radius:24px;box-shadow:0 8px 28px #17354b4d;padding:12px 17px;font:800 14px system-ui,sans-serif;cursor:pointer}
#afquote-trigger span{display:inline-grid;place-items:center;min-width:23px;height:23px;padding:0 5px;border-radius:20px;background:#fff;color:#075eaa}
#afquote-add{background:#eef8ff;color:#075b9d;border:2px solid #087fc2;min-height:44px;border-radius:12px;padding:10px 12px;font:800 13px system-ui,sans-serif;cursor:pointer}
.afquote-continue{background:#e6f3ff;border-color:#8cc8ed;color:#075b9d}#afquote-add:focus-visible,#afquote-trigger:focus-visible,.afquote-panel button:focus-visible,.afquote-panel input:focus-visible,.afquote-panel textarea:focus-visible{outline:3px solid #f6a300;outline-offset:2px}
#afquote-layer[hidden]{display:none!important}#afquote-layer{position:fixed;inset:0;z-index:120;font:14px system-ui,sans-serif;color:#153854}
.afquote-mask{position:absolute;inset:0;background:rgba(5,24,42,.62)}.afquote-panel{position:absolute;right:0;top:0;bottom:0;width:min(100%,465px);overflow:auto;background:white;box-shadow:-12px 0 40px #071a2a44;padding:22px 20px 40px;box-sizing:border-box}
.afquote-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.afquote-heading h2{font:900 23px system-ui,sans-serif;margin:0;color:#074e85}.afquote-panel button{cursor:pointer;font-family:inherit}.afquote-close{border:0;background:#eaf3fa;color:#123d60;border-radius:10px;font-size:24px;width:40px;height:40px}.afquote-hint{color:#5b7085;font-size:13px;line-height:1.5;margin:12px 0 19px}
.afquote-entry{display:grid;grid-template-columns:68px 1fr;gap:13px;padding:15px 0;border-bottom:1px solid #dde9f3}.afquote-entry img{width:68px;height:68px;object-fit:contain;background:#f5faff;border-radius:10px}.afquote-entry strong{display:block;font-size:14px;line-height:1.3;margin-bottom:8px}.afquote-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.afquote-row label{font-size:12px;font-weight:700}.afquote-qty{width:68px;padding:8px;border:1px solid #b5cbdc;border-radius:7px;font-size:16px}.afquote-remove{color:#ad2c3a;background:transparent;border:0;text-decoration:underline;padding:5px}.afquote-note{box-sizing:border-box;width:100%;min-height:58px;resize:vertical;border:1px solid #b5cbdc;border-radius:8px;margin-top:9px;padding:9px;font:13px system-ui,sans-serif}.afquote-note-label{font-size:12px;color:#496478;display:block;margin-top:10px}
.afquote-total{margin:16px 0 10px;font-size:13px;color:#56718b}.afquote-actions{display:grid;gap:9px}.afquote-primary{background:#18bf63!important;border:0!important;color:white!important;border-radius:11px!important;padding:13px;font-weight:850;font-size:15px}.afquote-primary:disabled{background:#a6b7ae!important;cursor:default}.afquote-secondary{background:#f0f6fb;border:1px solid #c6d9e7;border-radius:10px;padding:10px;color:#21516f;font-weight:700}.afquote-preview{width:100%;min-height:140px;box-sizing:border-box;resize:vertical;padding:12px;border:1px solid #a8c3d8;border-radius:10px;line-height:1.45;font:13px system-ui,sans-serif;margin:12px 0}.afquote-step[hidden]{display:none!important}.afquote-empty{padding:25px 12px;text-align:center;background:#f5faff;border-radius:12px;color:#53728d}.afquote-panel h3{font:800 16px system-ui,sans-serif;color:#124c79;margin:12px 0}
@media(max-width:620px){#afquote-trigger{right:12px;bottom:78px;padding:10px 13px;font-size:13px}.afquote-panel{padding:18px 14px 30px}#afquote-add{width:100%}}
'''

# Prefixo próprio e eventos nativos: não interfere na ficha e no rastreamento existentes.
JS = r'''
(function(){
  'use strict';
  const CONFIG=__CONFIG__;
  if(!document.querySelector('.product-card[data-detail-name]')||!document.getElementById('product-detail-modal'))return;
  const KEY='alphafest_orcamento_hf652423';
  const MAX_ITEMS=25;
  const esc=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clamp=(v)=>Math.max(1,Math.min(999,Math.floor(Number(v)||1)));
  let items=[];
  try{const saved=JSON.parse(localStorage.getItem(KEY)||'[]');if(Array.isArray(saved))items=saved.slice(0,MAX_ITEMS).filter(i=>i&&typeof i.name==='string').map(i=>({id:String(i.id||i.name).slice(0,180),name:i.name.slice(0,180),image:String(i.image||'').slice(0,600),quantity:clamp(i.quantity),note:String(i.note||'').slice(0,450)}));}catch(e){}
  function persist(){try{localStorage.setItem(KEY,JSON.stringify(items));}catch(e){} updateCount();}
  const layer=document.createElement('div');layer.id='afquote-layer';layer.hidden=true;layer.innerHTML=`<div class="afquote-mask" data-afquote-close></div><section class="afquote-panel" role="dialog" aria-modal="true" aria-labelledby="afquote-title"><div class="afquote-heading"><h2 id="afquote-title">🛒 Meu orçamento</h2><button type="button" class="afquote-close" data-afquote-close aria-label="Fechar">×</button></div><p class="afquote-hint">Junte produtos, informe as quantidades e personalize seu pedido. A AlphaFest confirmará valores, disponibilidade e prazo pelo WhatsApp.</p><div class="afquote-step" id="afquote-items-step"><div id="afquote-list"></div><p class="afquote-total" id="afquote-total"></p><div class="afquote-actions"><button type="button" class="afquote-primary" id="afquote-review">Revisar mensagem para WhatsApp</button><button type="button" class="afquote-secondary afquote-continue" id="afquote-continue">＋ Continuar escolhendo produtos</button><button type="button" class="afquote-secondary" id="afquote-clear">Limpar orçamento</button></div></div><div class="afquote-step" id="afquote-review-step" hidden><h3>Confira e edite antes de enviar</h3><label for="afquote-message">Mensagem do orçamento</label><textarea id="afquote-message" class="afquote-preview" maxlength="6000"></textarea><div class="afquote-actions"><button type="button" class="afquote-primary" id="afquote-send">💬 Abrir WhatsApp com esta mensagem</button><button type="button" class="afquote-secondary" id="afquote-back">Voltar e ajustar produtos</button><button type="button" class="afquote-secondary afquote-continue" id="afquote-continue-review">＋ Continuar escolhendo produtos</button></div><p class="afquote-hint">O pedido só será enviado se você confirmar o envio no WhatsApp. Não realizamos pagamento pelo site.</p></div></section>`;
  document.body.appendChild(layer);
  const trigger=document.createElement('button');trigger.id='afquote-trigger';trigger.type='button';trigger.setAttribute('aria-label','Abrir meu orçamento');trigger.innerHTML='🛒 Meu orçamento <span id="afquote-counter">0</span>';
  document.body.appendChild(trigger);
  const list=layer.querySelector('#afquote-list'),total=layer.querySelector('#afquote-total'),reviewStep=layer.querySelector('#afquote-review-step'),itemsStep=layer.querySelector('#afquote-items-step');
  let previousFocus=null;
  function updateCount(){trigger.querySelector('#afquote-counter').textContent=String(items.reduce((a,i)=>a+i.quantity,0));}
  function show(){previousFocus=document.activeElement;layer.hidden=false;reviewStep.hidden=true;itemsStep.hidden=false;render();layer.querySelector('.afquote-close').focus();}
  function hide(){layer.hidden=true;if(previousFocus&&previousFocus.focus)previousFocus.focus();}
  function render(){
    if(!items.length)list.innerHTML='<div class="afquote-empty">Seu orçamento está vazio. Abra um produto e clique em “Adicionar ao orçamento”.</div>';
    else list.innerHTML=items.map((i,j)=>`<div class="afquote-entry"><div>${i.image?'<img src="'+esc(i.image)+'" alt="" loading="lazy" onerror="this.hidden=true">':''}</div><div><strong>${esc(i.name)}</strong><div class="afquote-row"><label for="afquote-qty-${j}">Quantidade</label><input id="afquote-qty-${j}" class="afquote-qty" type="number" min="1" max="999" step="1" value="${i.quantity}" data-afqty="${j}"><button type="button" class="afquote-remove" data-afremove="${j}">Remover</button></div><label class="afquote-note-label" for="afquote-note-${j}">Nome, cor, tamanho ou outras observações</label><textarea id="afquote-note-${j}" class="afquote-note" maxlength="450" placeholder="Ex.: nome Ana, cor azul, para 30/11" data-afnote="${j}">${esc(i.note)}</textarea></div></div>`).join('');
    total.textContent=items.length?`${items.length} produto(s) diferente(s) · ${items.reduce((a,i)=>a+i.quantity,0)} unidade(s). Valores finais a confirmar com a AlphaFest.`:'';
    layer.querySelector('#afquote-review').disabled=!items.length;layer.querySelector('#afquote-clear').disabled=!items.length;
  }
  function campaignReferenceForCart(){
    try{
      const get=window.alphaFestCampaignReference;
      if(typeof get!=='function') return '';
      const reference=String(get()||'');
      if(reference.length>170 || !/^[a-z0-9][a-z0-9_-]*(?:\/[a-z0-9][a-z0-9_-]*){0,2}$/.test(reference)) return '';
      return reference;
    }catch(e){return '';}
  }
  function message(){
    const base='Olá! Gostaria de solicitar um orçamento na AlphaFest para os seguintes produtos:\n\n'+items.map((i,j)=>`${j+1}. ${i.name}\nQuantidade: ${i.quantity}${i.note?'\nPersonalização/observações: '+i.note:''}`).join('\n\n')+'\n\nPodem confirmar valores, disponibilidade, prazo e opções de retirada/entrega? Obrigado!';
    const ref=campaignReferenceForCart();
    const suffix=ref?'\n\nReferência da campanha: '+ref:'';
    return base.slice(0,6000-suffix.length)+suffix;
  }
  trigger.addEventListener('click',show);
  layer.querySelectorAll('[data-afquote-close]').forEach(b=>b.addEventListener('click',hide));
  layer.querySelectorAll('.afquote-continue').forEach(b=>b.addEventListener('click',()=>{hide();const modal=document.getElementById('product-detail-modal');if(modal && !modal.hidden){const close=modal.querySelector('[data-product-close]');if(close)close.click();}}));
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!layer.hidden){e.preventDefault();e.stopPropagation();hide();} if(e.key==='Tab'&&!layer.hidden){const nodes=[...layer.querySelectorAll('button:not([disabled]), input:not([disabled]), textarea:not([disabled])')].filter(x=>x.getClientRects().length);if(nodes.length){const a=nodes[0],z=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===a){e.preventDefault();z.focus();}else if(!e.shiftKey&&document.activeElement===z){e.preventDefault();a.focus();}}}},true);
  list.addEventListener('change',e=>{const idx=Number(e.target.dataset.afqty);if(e.target.matches('[data-afqty]')&&items[idx]){items[idx].quantity=clamp(e.target.value);persist();render();}});
  list.addEventListener('input',e=>{if(e.target.matches('[data-afnote]')){const idx=Number(e.target.dataset.afnote);if(items[idx]){items[idx].note=e.target.value.slice(0,450);persist();}}});
  list.addEventListener('click',e=>{const btn=e.target.closest('[data-afremove]');if(!btn)return;items.splice(Number(btn.dataset.afremove),1);persist();render();});
  layer.querySelector('#afquote-clear').addEventListener('click',()=>{if(!items.length||!confirm('Deseja limpar todos os itens do orçamento?'))return;items=[];persist();render();});
  layer.querySelector('#afquote-review').addEventListener('click',()=>{if(!items.length)return;layer.querySelector('#afquote-message').value=message().slice(0,6000);itemsStep.hidden=true;reviewStep.hidden=false;layer.querySelector('#afquote-message').focus();});
  layer.querySelector('#afquote-back').addEventListener('click',()=>{reviewStep.hidden=true;itemsStep.hidden=false;render();});
  layer.querySelector('#afquote-send').addEventListener('click',()=>{const msg=layer.querySelector('#afquote-message').value.trim();if(!msg)return; if(!CONFIG.number){alert('WhatsApp temporariamente indisponível. Fale com a AlphaFest pelo botão de contato do site.');return;}const url='https://wa.me/'+CONFIG.number+'?text='+encodeURIComponent(msg);window.dispatchEvent(new CustomEvent('alphafest:metric',{detail:{type:'whatsapp_click',product:'Orçamento com '+items.length+' produtos',context:'carrinho'}}));const win=window.open(url,'_blank','noopener,noreferrer');if(!win)window.location.href=url;});
  const modal=document.getElementById('product-detail-modal');
  const actions=modal.querySelector('.product-detail-actions');
  if(actions){const add=document.createElement('button');add.type='button';add.id='afquote-add';add.textContent='＋ Adicionar ao orçamento';actions.appendChild(add);add.addEventListener('click',()=>{
    const name=(modal.querySelector('#product-detail-name')?.textContent||'').trim();if(!name)return;
    const current=[...document.querySelectorAll('.product-card[data-detail-name]')].find(c=>c.dataset.detailName===name);
    const id=(current?.dataset.product||name).slice(0,180);const image=(current?.dataset.detailImage||'').slice(0,600);
    const existing=items.find(i=>i.id===id);if(existing)existing.quantity=Math.min(999,existing.quantity+1);
    else if(items.length>=MAX_ITEMS){alert('Limite de '+MAX_ITEMS+' produtos diferentes no orçamento.');return;}
    else items.push({id,name,image:image.startsWith('data:')?'':image,quantity:1,note:''});
    persist();show();
  });}
  updateCount();
})();
'''


def inject_cart(page: str, empresa: dict | None) -> str:
    """Adiciona UI isolada ao HTML já montado, sem alterar CTAs anteriores."""
    if not page or 'id="afquote-js"' in page or '</body>' not in page:
        return page
    empresa = empresa or {}
    numero = re.sub(r'\D', '', str(empresa.get('whatsapp_catalogo') or empresa.get('celular') or ''))
    if numero and not numero.startswith('55'):
        numero = '55' + numero
    script = JS.replace('__CONFIG__', json.dumps({'number': numero}, ensure_ascii=False))
    page = page.replace('</head>', '<style id="afquote-css">'+CSS+'</style></head>', 1)
    return page.replace('</body>', '<script id="afquote-js">'+script+'</script></body>', 1)
