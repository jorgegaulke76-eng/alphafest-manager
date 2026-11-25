"""HF65.24.55 — Carrinho com linhas independentes de personalização.

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
.afquote-entry{display:grid;grid-template-columns:68px minmax(0,1fr);gap:13px;padding:15px 0;border-bottom:1px solid #dde9f3}.afquote-entry-noimage{grid-template-columns:minmax(0,1fr)}.afquote-entry-noimage>div:first-child{display:none}.afquote-entry img{width:68px;height:68px;object-fit:contain;background:#f5faff;border-radius:10px}.afquote-entry strong{display:block;font-size:14px;line-height:1.3;margin-bottom:8px;overflow-wrap:anywhere}.afquote-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.afquote-row label{font-size:12px;font-weight:700}.afquote-qty{width:68px;padding:8px;border:1px solid #b5cbdc;border-radius:7px;font-size:16px}.afquote-remove{color:#ad2c3a;background:transparent;border:0;text-decoration:underline;padding:8px;min-height:44px}.afquote-note{box-sizing:border-box;width:100%;min-height:70px;resize:vertical;border:1px solid #b5cbdc;border-radius:8px;margin-top:7px;padding:9px;font:16px system-ui,sans-serif}.afquote-note-label{font-size:12px;color:#496478;display:block;margin-top:10px}.afquote-another{margin-top:9px;min-height:44px;width:100%;font-size:13px}.afquote-item-label{display:block;font-size:11px;color:#56718b;margin-bottom:5px}.afquote-notice{padding:11px 12px;border:1px solid #b4d7ee;border-radius:10px;background:#eef8ff;color:#164f74;line-height:1.45}.afquote-notice[hidden]{display:none!important}
.afquote-total{margin:16px 0 10px;font-size:13px;color:#56718b}.afquote-actions{display:grid;gap:9px}.afquote-primary{background:#18bf63!important;border:0!important;color:white!important;border-radius:11px!important;padding:13px;font-weight:850;font-size:15px}.afquote-primary:disabled{background:#a6b7ae!important;cursor:default}.afquote-secondary{background:#f0f6fb;border:1px solid #c6d9e7;border-radius:10px;padding:10px;color:#21516f;font-weight:700}.afquote-preview{width:100%;min-height:140px;box-sizing:border-box;resize:vertical;padding:12px;border:1px solid #a8c3d8;border-radius:10px;line-height:1.45;font:13px system-ui,sans-serif;margin:12px 0}.afquote-step[hidden]{display:none!important}.afquote-empty{padding:25px 12px;text-align:center;background:#f5faff;border-radius:12px;color:#53728d}.afquote-panel h3{font:800 16px system-ui,sans-serif;color:#124c79;margin:12px 0}
.afquote-message-help{background:#fff7dc;border:1px solid #ebd387;border-radius:10px;padding:12px;color:#654b10;line-height:1.5}.afquote-copy-status{color:#075b48;font-size:13px;line-height:1.5}.afquote-message-help[hidden],.afquote-copy-status[hidden]{display:none!important}.afquote-secondary:disabled{opacity:.55;cursor:default}
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
  // Limite conservador da URL preenchida, não do conteúdo do orçamento.
  const MAX_WHATSAPP_URL_LENGTH=3500;
  const esc=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clamp=(v)=>Math.max(1,Math.min(999,Math.floor(Number(v)||1)));
  const validLineId=id=>typeof id==='string'&&/^[a-zA-Z0-9_-]{1,80}$/.test(id);
  const reservedLineIds=new Set();let lineSequence=0;
  function newLineId(){let id;do{id='afq-'+(++lineSequence);}while(reservedLineIds.has(id));reservedLineIds.add(id);return id;}
  let items=[],loaded=false;
  // A chave e o campo id continuam os mesmos: id é o produto; lineId é a linha.
  // Não mescla personalizações nem descarta linhas salvas ao migrar/recarregar.
  try{
    const saved=JSON.parse(localStorage.getItem(KEY)||'[]');
    if(Array.isArray(saved)){
      saved.forEach(i=>{if(i&&validLineId(i.lineId))reservedLineIds.add(i.lineId);});
      const seen=new Set();
      items=saved.filter(i=>i&&typeof i.name==='string').map(i=>{
        const lineId=validLineId(i.lineId)&&!seen.has(i.lineId)?i.lineId:newLineId();seen.add(lineId);
        return {id:String(i.id||i.name).slice(0,180),lineId,name:i.name.slice(0,180),image:String(i.image||'').slice(0,600),quantity:clamp(i.quantity),note:String(i.note||'').slice(0,450)};
      });loaded=true;
    }
  }catch(e){}
  function persist(){try{localStorage.setItem(KEY,JSON.stringify(items));}catch(e){} updateCount();}
  const layer=document.createElement('div');layer.id='afquote-layer';layer.hidden=true;layer.innerHTML=`<div class="afquote-mask" data-afquote-close></div><section class="afquote-panel" role="dialog" aria-modal="true" aria-labelledby="afquote-title"><div class="afquote-heading"><h2 id="afquote-title">🛒 Meu orçamento</h2><button type="button" class="afquote-close" data-afquote-close aria-label="Fechar">×</button></div><p class="afquote-hint">Ajuste a quantidade para itens iguais. Para outro nome, cor ou tamanho do mesmo produto, use “Outra personalização”. Cada personalização fica em uma linha separada.</p><div class="afquote-step" id="afquote-items-step"><p id="afquote-notice" class="afquote-notice" role="status" aria-live="polite" aria-atomic="true" hidden></p><div id="afquote-list"></div><p class="afquote-total" id="afquote-total"></p><div class="afquote-actions"><button type="button" class="afquote-primary" id="afquote-review">Revisar mensagem para WhatsApp</button><button type="button" class="afquote-secondary afquote-continue" id="afquote-continue">＋ Continuar escolhendo produtos</button><button type="button" class="afquote-secondary" id="afquote-clear">Limpar orçamento</button></div></div><div class="afquote-step" id="afquote-review-step" hidden><h3>Confira e edite antes de enviar</h3><label for="afquote-message">Mensagem do orçamento</label><textarea id="afquote-message" class="afquote-preview" aria-describedby="afquote-message-help"></textarea><p id="afquote-message-help" class="afquote-message-help" role="status" hidden>Seu orçamento é longo e está completo. Primeiro copie a mensagem; depois abra o WhatsApp e cole o texto na conversa. Nenhum item será removido.</p><div class="afquote-actions"><button type="button" class="afquote-secondary" id="afquote-copy">Copiar mensagem completa</button><button type="button" class="afquote-primary" id="afquote-send">💬 Abrir WhatsApp com esta mensagem</button><button type="button" class="afquote-secondary" id="afquote-back">Voltar e ajustar produtos</button><button type="button" class="afquote-secondary afquote-continue" id="afquote-continue-review">＋ Continuar escolhendo produtos</button></div><p id="afquote-copy-status" class="afquote-copy-status" role="status" hidden></p><p class="afquote-hint">A AlphaFest confirmará valores, disponibilidade e prazo. O pedido só será enviado se você confirmar o envio no WhatsApp. Não realizamos pagamento pelo site.</p></div></section>`;
  document.body.appendChild(layer);
  const trigger=document.createElement('button');trigger.id='afquote-trigger';trigger.type='button';trigger.setAttribute('aria-label','Abrir meu orçamento');trigger.innerHTML='🛒 Meu orçamento <span id="afquote-counter">0</span>';
  document.body.appendChild(trigger);
  const list=layer.querySelector('#afquote-list'),total=layer.querySelector('#afquote-total'),reviewStep=layer.querySelector('#afquote-review-step'),itemsStep=layer.querySelector('#afquote-items-step');
  const messageInput=layer.querySelector('#afquote-message'),messageHelp=layer.querySelector('#afquote-message-help'),copyStatus=layer.querySelector('#afquote-copy-status'),copyButton=layer.querySelector('#afquote-copy'),sendButton=layer.querySelector('#afquote-send');
  const notice=layer.querySelector('#afquote-notice');
  let previousFocus=null;
  function announce(text){notice.textContent=text;notice.hidden=!text;}
  function limitMessage(){return 'Limite de '+MAX_ITEMS+' itens/personalizações no orçamento. Remova itens antes de incluir outra linha.';}
  function updateCount(){const count=items.reduce((a,i)=>a+i.quantity,0);trigger.querySelector('#afquote-counter').textContent=String(count);trigger.setAttribute('aria-label','Abrir meu orçamento: '+items.length+' itens/personalizações, '+count+' unidades');}
  function show(text=''){previousFocus=document.activeElement;layer.hidden=false;reviewStep.hidden=true;itemsStep.hidden=false;render();announce([typeof text==='string'?text:'',items.length>=MAX_ITEMS?limitMessage():''].filter(Boolean).join(' '));layer.querySelector('.afquote-close').focus();}
  function hide(){layer.hidden=true;if(previousFocus&&previousFocus.focus)previousFocus.focus();}
  function focusLine(lineId,field='note'){const input=document.getElementById('afquote-'+field+'-'+lineId);if(input){input.focus();if(input.scrollIntoView)input.scrollIntoView({block:'nearest'});}}
  function totals(){
    const units=items.reduce((a,i)=>a+i.quantity,0);
    total.textContent=items.length?`${items.length} ${items.length===1?'item/personalização':'itens/personalizações'} · ${units} ${units===1?'unidade':'unidades'}. Limite: ${MAX_ITEMS} itens. Valores finais a confirmar com a AlphaFest.`:'';
    layer.querySelector('#afquote-review').disabled=!items.length;layer.querySelector('#afquote-clear').disabled=!items.length;
  }
  function render(){
    if(!items.length)list.innerHTML='<div class="afquote-empty">Seu orçamento está vazio. Abra um produto e clique em “Adicionar ao orçamento”.</div>';
    else list.innerHTML=items.map((i,j)=>`<div class="afquote-entry${i.image?'':' afquote-entry-noimage'}" data-afline="${i.lineId}"><div>${i.image?'<img src="'+esc(i.image)+'" alt="" loading="lazy" onerror="this.hidden=true">':''}</div><div><span class="afquote-item-label">Item ${j+1}</span><strong id="afquote-name-${i.lineId}">${esc(i.name)}</strong><div class="afquote-row"><label for="afquote-qty-${i.lineId}">Quantidade</label><input id="afquote-qty-${i.lineId}" class="afquote-qty" type="number" inputmode="numeric" min="1" max="999" step="1" value="${i.quantity}" data-afqty="${i.lineId}" aria-describedby="afquote-name-${i.lineId}"><button type="button" class="afquote-remove" data-afremove="${i.lineId}" aria-label="Remover item ${j+1}: ${esc(i.name)}">Remover</button></div><label class="afquote-note-label" for="afquote-note-${i.lineId}">Nome, cor, tamanho ou outras observações</label><textarea id="afquote-note-${i.lineId}" class="afquote-note" maxlength="450" placeholder="Ex.: nome Ana, cor azul, para 30/11" data-afnote="${i.lineId}" aria-describedby="afquote-name-${i.lineId}">${esc(i.note)}</textarea><button type="button" class="afquote-secondary afquote-another" data-afanother="${i.lineId}" aria-label="Outra personalização de ${esc(i.name)}"${items.length>=MAX_ITEMS?' disabled title="Limite de 25 itens/personalizações atingido"':''}>＋ Outra personalização</button></div></div>`).join('');
    totals();
  }
  function message(){return 'Olá! Gostaria de solicitar um orçamento na AlphaFest para os seguintes produtos:\n\n'+items.map((i,j)=>`${j+1}. ${i.name}\nQuantidade: ${i.quantity}${i.note?'\nPersonalização/observações: '+i.note:''}`).join('\n\n')+'\n\nPodem confirmar valores, disponibilidade, prazo e opções de retirada/entrega? Obrigado!';}
  function messageState(){
    const msg=messageInput.value.trim();
    let url='';
    try{url='https://wa.me/'+CONFIG.number+'?text='+encodeURIComponent(msg);}catch(e){}
    const long=Boolean(msg)&&(!url||url.length>MAX_WHATSAPP_URL_LENGTH);
    messageHelp.hidden=!long;
    sendButton.textContent=long?'💬 Abrir WhatsApp para colar':'💬 Abrir WhatsApp com esta mensagem';
    sendButton.disabled=!msg;copyButton.disabled=!msg;
    return {msg,url,long};
  }
  async function copyMessage(){
    if(!messageInput.value.trim())return;
    let copied=false;
    try{if(navigator.clipboard&&navigator.clipboard.writeText){await navigator.clipboard.writeText(messageInput.value);copied=true;}}catch(e){}
    if(!copied){
      messageInput.focus();messageInput.select();
      try{copied=Boolean(document.execCommand&&document.execCommand('copy'));}catch(e){}
    }
    copyStatus.hidden=false;
    copyStatus.textContent=copied?'Mensagem completa copiada. Abra o WhatsApp e cole o texto na conversa.':'A mensagem completa está selecionada. Use a opção Copiar do seu aparelho e depois cole no WhatsApp.';
  }
  trigger.addEventListener('click',show);
  layer.querySelectorAll('[data-afquote-close]').forEach(b=>b.addEventListener('click',hide));
  layer.querySelectorAll('.afquote-continue').forEach(b=>b.addEventListener('click',()=>{hide();const modal=document.getElementById('product-detail-modal');if(modal && !modal.hidden){const close=modal.querySelector('[data-product-close]');if(close)close.click();}}));
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!layer.hidden){e.preventDefault();e.stopPropagation();hide();} if(e.key==='Tab'&&!layer.hidden){const nodes=[...layer.querySelectorAll('button:not([disabled]), input:not([disabled]), textarea:not([disabled])')].filter(x=>x.getClientRects().length);if(nodes.length){const a=nodes[0],z=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===a){e.preventDefault();z.focus();}else if(!e.shiftKey&&document.activeElement===z){e.preventDefault();a.focus();}}}},true);
  list.addEventListener('change',e=>{
    if(!e.target.matches('[data-afqty]'))return;
    const item=items.find(i=>i.lineId===e.target.dataset.afqty);if(!item)return;
    const quantity=Number(e.target.value);
    if(!Number.isInteger(quantity)||quantity<1||quantity>999){e.target.value=String(item.quantity);announce('Use uma quantidade inteira de 1 a 999. A quantidade anterior foi mantida.');return;}
    item.quantity=quantity;persist();totals();announce('Quantidade atualizada para este item.');
  });
  list.addEventListener('input',e=>{if(e.target.matches('[data-afnote]')){const item=items.find(i=>i.lineId===e.target.dataset.afnote);if(item){item.note=e.target.value.slice(0,450);persist();}}});
  list.addEventListener('click',e=>{
    const remove=e.target.closest('[data-afremove]');
    if(remove){
      const index=items.findIndex(i=>i.lineId===remove.dataset.afremove);if(index<0)return;
      items.splice(index,1);persist();render();announce('Item removido.');
      if(items.length)focusLine(items[Math.min(index,items.length-1)].lineId,'qty');else layer.querySelector('#afquote-continue').focus();return;
    }
    const another=e.target.closest('[data-afanother]');if(!another)return;
    const index=items.findIndex(i=>i.lineId===another.dataset.afanother);if(index<0)return;
    if(items.length>=MAX_ITEMS){announce(limitMessage());return;}
    const source=items[index],fresh={id:source.id,lineId:newLineId(),name:source.name,image:source.image,quantity:1,note:''};
    items.splice(index+1,0,fresh);persist();render();announce('Outra personalização adicionada. Preencha as observações da nova linha.'+(items.length>=MAX_ITEMS?' '+limitMessage():''));focusLine(fresh.lineId);
  });
  layer.querySelector('#afquote-clear').addEventListener('click',()=>{if(!items.length||!confirm('Deseja limpar todos os itens do orçamento?'))return;items=[];persist();render();announce('Orçamento limpo.');layer.querySelector('#afquote-continue').focus();});
  layer.querySelector('#afquote-review').addEventListener('click',()=>{if(!items.length)return;messageInput.value=message();copyStatus.hidden=true;messageState();itemsStep.hidden=true;reviewStep.hidden=false;messageInput.focus();});
  layer.querySelector('#afquote-back').addEventListener('click',()=>{reviewStep.hidden=true;itemsStep.hidden=false;render();});
  messageInput.addEventListener('input',()=>{copyStatus.hidden=true;messageState();});
  copyButton.addEventListener('click',copyMessage);
  sendButton.addEventListener('click',()=>{const state=messageState();if(!state.msg)return;if(!CONFIG.number){alert('WhatsApp temporariamente indisponível. Fale com a AlphaFest pelo botão de contato do site.');return;}const url=state.long?'https://wa.me/'+CONFIG.number:state.url;window.dispatchEvent(new CustomEvent('alphafest:metric',{detail:{type:'whatsapp_click',product:'Orçamento com '+items.length+' itens/personalizações',context:'carrinho'}}));const win=window.open(url,'_blank','noopener,noreferrer');if(!win)window.location.href=url;});
  const modal=document.getElementById('product-detail-modal');
  const actions=modal.querySelector('.product-detail-actions');
  if(actions){const add=document.createElement('button');add.type='button';add.id='afquote-add';add.textContent='＋ Adicionar ao orçamento';actions.appendChild(add);add.addEventListener('click',()=>{
    const product=modal.dataset.product;
    const matches=product?[...document.querySelectorAll('.product-card[data-detail-name]')].filter(c=>c.dataset.product===product):[];
    const current=matches.length===1?matches[0]:null;
    if(!current){alert(matches.length>1?'Este produto tem uma identificação repetida na vitrine. Use Pedir orçamento deste produto para consultar os detalhes com a AlphaFest. Nenhum item foi adicionado.':'Abra novamente a ficha do produto para adicioná-lo ao orçamento.');return;}
    const id=String(product).slice(0,180),name=String(current.dataset.detailName||'').slice(0,180);if(!name)return;
    const existing=items.filter(i=>i.id===id);
    if(existing.length){show('Este produto já está no orçamento. Ajuste a quantidade da linha desejada ou use “Outra personalização” para outro nome, cor ou tamanho. Nenhuma quantidade foi alterada.');focusLine(existing[0].lineId,'qty');return;}
    if(items.length>=MAX_ITEMS){show();return;}
    const image=String(current.dataset.detailImage||'').slice(0,600),fresh={id,lineId:newLineId(),name,image:image.startsWith('data:')?'':image,quantity:1,note:''};
    items.push(fresh);persist();show('Produto adicionado. Informe a personalização desta linha.');focusLine(fresh.lineId);
  });}
  if(loaded)persist();else updateCount();
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
