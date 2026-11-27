"""HF55: DOM funcional offline, scripts reais da ficha/carrinho e importador HF54."""
from copy import deepcopy
import json
import re
import shutil
import subprocess
import unittest

from site_carrinho_orcamento_service import inject_cart
from site_quote_import_service import analisar_mensagem, preparar_rascunho
from site_vitrine_service import gerar_html_vitrine


CATALOG = [
    {"Nome": "Caneca Personalizada", "CatalogoId": "CAT-01", "Preco": 18.5,
     "DescricaoCompleta": "Escolha o nome e a cor de cada caneca.",
     "Categoria": "PERSONALIZADOS", "Subcategoria": "PRESENTES",
     "Imagens": ["https://example.invalid/caneca.png"], "PublicarSite": True, "Ativo": True},
    {"Nome": "Chaveiro Personalizado", "CatalogoId": "CAT-02", "Preco": 8.0,
     "DescricaoCompleta": "Um chaveiro para cada convidado.",
     "Categoria": "PERSONALIZADOS", "Subcategoria": "PRESENTES",
     "Imagens": ["https://example.invalid/chaveiro.png"], "PublicarSite": True, "Ativo": True},
]


def fixture_page(*, catalog=None, gallery=False):
    """Dados fictícios; os dois scripts e o HTML vêm dos geradores usados no site."""
    company = {"nome": "AlphaFest · teste de personalizações", "celular": "11999991234"}
    page = gerar_html_vitrine(
        CATALOG if catalog is None else catalog, company, modo_preview=True,
        usar_taxonomia_catalogo=True,
        produtos_com_galeria=["Caneca Personalizada"] if gallery else [],
    )
    return inject_cart(page, company)


# O DOM interpreta os elementos e atributos emitidos; não recria funções do
# carrinho. Eventos propagam até os listeners delegados, foco considera os
# elementos presentes e recarregar cria um documento/VM novo com o mesmo storage.
_RUNNER = r'''
(async function(){
const vm=require('vm'),input=JSON.parse(require('fs').readFileSync(0,'utf8'));
const KEY='alphafest_orcamento_hf652423';
const REVIEW_KEY='alphafest_orcamento_mensagem_hf652456';
let stored=input.rawStorage===undefined?JSON.stringify(input.items||[]):input.rawStorage;
let reviewStored=input.rawReviewStorage===undefined?null:input.rawReviewStorage;
const writes=[],reviewWrites=[],opened=[],copied=[],metrics=[],alerts=[],confirms=[];
function createPage(){
  let document;
  const decode=s=>String(s).replace(/&(amp|lt|gt|quot|apos|#39|#\d+|#x[\da-f]+);/gi,(all,key)=>{
    const entities={amp:'&',lt:'<',gt:'>',quot:'"',apos:"'",'#39':"'"};
    if(key[0]==='#'&&key!=='#39')return String.fromCodePoint(key[1].toLowerCase()==='x'?parseInt(key.slice(2),16):parseInt(key.slice(1),10));
    return entities[key]??all;
  });
  function camel(s){return s.replace(/-([a-z])/g,(_,c)=>c.toUpperCase());}
  class Element {
    constructor(tag){
      this.tagName=tag.toLowerCase();this.attrs={};this.dataset={};this.children=[];this.parent=null;
      this.listeners={};this.hidden=false;this.disabled=false;this.value='';this.id='';this.className='';
      this.style={removeProperty(key){delete this[key];}};
      this.classList={add:(...names)=>{this.className=[...new Set(this.className.split(/\s+/).filter(Boolean).concat(names))].join(' ');},remove:(...names)=>{this.className=this.className.split(/\s+/).filter(n=>!names.includes(n)).join(' ');},contains:name=>this.className.split(/\s+/).includes(name)};
    }
    setAttribute(name,value){
      value=String(value);this.attrs[name]=value;
      if(name.startsWith('data-'))this.dataset[camel(name.slice(5))]=value;
      else if(name==='class')this.className=value;
      else if(name==='hidden'||name==='disabled')this[name]=true;
      else this[name]=value;
    }
    getAttribute(name){
      if(name.startsWith('data-'))return this.dataset[camel(name.slice(5))]??null;
      if(name==='id')return this.id||null;if(name==='class')return this.className||null;
      if(name==='hidden'||name==='disabled')return this[name]?'':null;
      return this.attrs[name]??null;
    }
    removeAttribute(name){delete this.attrs[name];if(name==='hidden'||name==='disabled')this[name]=false;else delete this[name];}
    appendChild(child){child.parent=this;this.children.push(child);return child;}
    set textContent(value){this._text=String(value);this.children=[];}
    get textContent(){return (this._text||'')+this.children.map(c=>c.textContent).join('');}
    set innerHTML(value){this._html=String(value);this._text='';this.children=[];parse(this,String(value));}
    get innerHTML(){return this._html||'';}
    matches(selector){
      selector=selector.trim();
      if(selector.includes(':not([disabled])')){if(this.disabled)return false;selector=selector.replace(':not([disabled])','');}
      const tag=selector.match(/^[a-zA-Z][\w-]*/);if(tag&&this.tagName!==tag[0].toLowerCase())return false;
      const id=selector.match(/#([\w-]+)/);if(id&&this.id!==id[1])return false;
      for(const c of selector.matchAll(/\.([\w-]+)/g))if(!this.className.split(/\s+/).includes(c[1]))return false;
      for(const a of selector.matchAll(/\[([^\]=]+)(?:=["']?([^\]"']*)["']?)?\]/g)){
        const value=this.getAttribute(a[1]);if(value===null||(a[2]!==undefined&&value!==a[2]))return false;
      }
      return this.tagName!=='#text';
    }
    querySelectorAll(selector){const choices=selector.split(','),out=[];function visit(node){for(const c of node.children){if(choices.some(s=>c.matches(s)))out.push(c);visit(c);}}visit(this);return out;}
    querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
    closest(selector){let value=this;while(value){if(value.matches(selector))return value;value=value.parent;}return null;}
    addEventListener(type,fn,options={}){(this.listeners[type]??=[]).push({fn,capture:options===true||!!options.capture,once:!!options.once});}
    fire(type,event={}){
      const pending=[];event.type=type;event.target??=this;event.preventDefault??=()=>{event.defaultPrevented=true;};event.stopPropagation??=()=>{event.stopped=true;};
      const path=[];for(let p=this;p;p=p.parent)path.push(p);
      function invoke(node,capture){for(const listener of [...(node.listeners[type]||[])])if(listener.capture===capture){if(listener.once)node.listeners[type]=node.listeners[type].filter(x=>x!==listener);const result=listener.fn(event);if(result&&result.then)pending.push(result);}}
      for(const node of [...path].reverse()){invoke(node,true);if(event.stopped)break;}
      if(!event.stopped)for(const node of path){invoke(node,false);if(event.stopped)break;}
      return Promise.all(pending);
    }
    click(){if(this.disabled)return Promise.resolve();return this.fire('click');}
    focus(){document.activeElement=this;}
    select(){this.selected=true;}
    scrollIntoView(){this.scrolled=true;}
    getClientRects(){for(let p=this;p;p=p.parent)if(p.hidden)return [];return [{}];}
  }
  function parse(root,html){
    const stack=[root],voids=new Set(['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']);
    for(const token of html.matchAll(/<!--[\s\S]*?-->|<![^>]*>|<[^>]+>|[^<]+/g)){
      const text=token[0];if(text.startsWith('<!'))continue;
      if(text.startsWith('</')){const tag=text.slice(2,-1).trim().toLowerCase();if(stack.length>1&&stack[stack.length-1].tagName===tag){const closed=stack.pop();if(tag==='textarea')closed.value=closed.textContent;}continue;}
      if(text.startsWith('<')){
        const tag=text.match(/^<([\w-]+)/)?.[1];if(!tag)continue;
        const node=new Element(tag);
        for(const a of text.slice(tag.length+1,-1).matchAll(/([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g))node.setAttribute(a[1],decode(a[2]??a[3]??a[4]??''));
        stack[stack.length-1].appendChild(node);if(!voids.has(tag.toLowerCase())&&!text.endsWith('/>'))stack.push(node);
      }else{const node=new Element('#text');node.textContent=decode(text);stack[stack.length-1].appendChild(node);}
    }
  }
  document=new Element('document');document.readyState=input.readyState||'complete';
  parse(document,input.html);document.body=document.querySelector('body');document.activeElement=document.body;
  document.getElementById=id=>document.querySelector('#'+id);document.createElement=tag=>new Element(tag);
  document.execCommand=()=>{if(input.clipboard==='manual')return false;copied.push(document.activeElement.value);return true;};
  const get=id=>document.getElementById(id);
  const cards=document.querySelectorAll('.product-card[data-detail-name]');
  (input.cardOverrides||[]).forEach((overrides,i)=>Object.assign(cards[i].dataset,overrides));
  const window=new Element('window');window.location={search:input.query||'',href:''};window.matchMedia=()=>({matches:!!input.mobile});
  window.visualViewport=Object.assign(new Element('viewport'),{offsetLeft:0,offsetTop:0,width:390,height:720});
  window.open=url=>{opened.push(url);return {};};window.dispatchEvent=e=>metrics.push(e.detail);
  const localStorage={
    getItem(key){if(key!==KEY&&key!==REVIEW_KEY)throw new Error('Chave de storage alterada');if(input.failStorageRead===true||input.failStorageRead===key)throw new Error('Leitura indisponível');return key===KEY?stored:reviewStored;},
    setItem(key,value){if(key!==KEY&&key!==REVIEW_KEY)throw new Error('Chave de storage alterada');if(input.failStorageWrite===true||input.failStorageWrite===key)throw new Error('Gravação indisponível');if(key===KEY){stored=value;writes.push(value);}else{reviewStored=value;reviewWrites.push(value);}}
  };
  const navigator={clipboard:{async writeText(value){if(input.clipboard==='manual'||input.clipboard==='fallback')throw new Error('Sem permissão');copied.push(value);}}};
  class CustomEvent{constructor(type,options){this.type=type;this.detail=options.detail;}}
  const context=vm.createContext({document,window,localStorage,navigator,CustomEvent,URLSearchParams,alert:m=>alerts.push(m),confirm:m=>{confirms.push(m);return input.confirm!==false;}});
  vm.runInContext(input.detailScript,context,{timeout:1000});
  vm.runInContext(input.cartScript,context,{timeout:1000});
  const entries=()=>get('afquote-list').querySelectorAll('[data-afline]');
  function state(){
    return {items:JSON.parse(stored||'[]'),rows:entries().map(row=>({lineId:row.dataset.afline,quantity:row.querySelector('[data-afqty]').value,note:row.querySelector('[data-afnote]').value,anotherDisabled:row.querySelector('[data-afanother]').disabled})),
      count:get('afquote-counter').textContent,total:get('afquote-total').textContent,notice:get('afquote-notice').textContent,noticeHidden:get('afquote-notice').hidden,
      focused:document.activeElement.id,scrolled:!!document.activeElement.scrolled,html:get('afquote-list').innerHTML,
      message:get('afquote-message').value,reviewDisabled:get('afquote-review').disabled,clearDisabled:get('afquote-clear').disabled,
      readOnly:!!get('afquote-message').readOnly,selected:!!get('afquote-message').selected,sendDisabled:get('afquote-send').disabled,sendLabel:get('afquote-send').textContent,helpHidden:get('afquote-message-help').hidden,
      reviewWarning:get('afquote-review-warning').textContent,warningHidden:get('afquote-review-warning').hidden,regenerateHidden:get('afquote-regenerate').hidden,regenerateDisabled:get('afquote-regenerate').disabled,
      historyHidden:get('afquote-history').hidden,historyText:get('afquote-history-message').value,historySelected:!!get('afquote-history-message').selected,historyOptions:get('afquote-history-select').querySelectorAll('option').map(option=>({value:option.value,text:option.textContent})),historyValue:get('afquote-history-select').value,historyStatus:get('afquote-history-status').textContent,
      storageNote:get('afquote-storage-note').textContent,storageNoteHidden:get('afquote-storage-note').hidden,reviewStorage:reviewStored,reviewWrites:reviewWrites.length,
      injected:!!document.querySelector('#injected'),copyStatus:get('afquote-copy-status').textContent,confirms:[...confirms],
      hidden:get('afquote-layer').hidden,modalHidden:get('product-detail-modal').hidden,product:get('product-detail-modal').dataset.product,
      opened:[...opened],copied:[...copied],metrics:[...metrics],alerts:[...alerts],storageWrites:writes.length};
  }
  async function act(action){
    const row=()=>{const value=entries()[action.row??0];if(!value)throw new Error('Linha ausente: '+JSON.stringify(action));return value;};
    if(action.event==='open'||action.event==='enter'){
      const card=cards.find(c=>c.dataset.product===action.product);if(!card)throw new Error('Produto ausente');
      if(action.event==='open')await card.click();else await card.fire('keydown',{key:'Enter'});
    }else if(action.event==='related')await get('product-related-grid').querySelectorAll('button')[action.index??0].click();
    else if(action.event==='quantity'||action.event==='note'){
      const field=row().querySelector(action.event==='quantity'?'[data-afqty]':'[data-afnote]');field.value=String(action.value);await field.fire(action.event==='quantity'?'change':'input');
    }else if(action.event==='another'||action.event==='remove')await row().querySelector(action.event==='another'?'[data-afanother]':'[data-afremove]').click();
    else if(action.event==='stale-remove'||action.event==='force-another'){
      const button=new Element('button');button.dataset[action.event==='stale-remove'?'afremove':'afanother']=action.lineId;await get('afquote-list').fire('click',{target:button});
    }else if(action.event==='dom-ready'){document.readyState='interactive';await document.fire('DOMContentLoaded');}
    else if(action.event==='edit'){get('afquote-message').value=String(action.text);await get('afquote-message').fire('input');}
    else if(action.event==='history-select'){get('afquote-history-select').value=String(action.index);await get('afquote-history-select').fire('change');}
    else if(action.event==='force-send')await get('afquote-send').fire('click');
    else if(action.event==='force-regenerate')await get('afquote-regenerate').fire('click');
    else if(action.event==='storage-items')stored=JSON.stringify(action.items);
    else if(action.event==='storage-review')reviewStored=action.raw;
    else if(action.event==='key'){if(action.focus)get(action.focus).focus();await document.fire('keydown',{key:action.key,shiftKey:!!action.shift});}
    else if(action.event==='missing-id')delete get('product-detail-modal').dataset.product;
    else if(action.event==='show')await get('afquote-trigger').click();
    else if(action.event==='close')await get('afquote-layer').querySelector('.afquote-close').click();
    else await get('afquote-'+action.event).click();
  }
  return {state,act};
}
let page=createPage();const states=[page.state()];
for(const action of input.actions){if(action.event==='reload')page=createPage();else await page.act(action);states.push(page.state());}
process.stdout.write(JSON.stringify(states));
})().catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
'''


class SiteCartPersonalizationsHF55Tests(unittest.TestCase):
    def run_cart(self, items=(), actions=(), **options):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node local necessário para executar os scripts reais do site")
        page = fixture_page(catalog=options.pop("catalog", None), gallery=options.pop("gallery", False))
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", page, re.S)
        detail_script = next(s for s in scripts if "function open(card)" in s)
        cart_script = next(s for s in scripts if "const KEY='alphafest_orcamento_hf652423'" in s)
        html = re.sub(r"<(script|style)\b[^>]*>[\s\S]*?</\1>", "", page)
        payload = {"html": html, "detailScript": detail_script, "cartScript": cart_script,
                   "items": items, "actions": actions, **options}
        result = subprocess.run([node, "-e", _RUNNER], input=json.dumps(payload), text=True,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    @staticmethod
    def item(index=1, *, product="caneca-personalizada", note="Nome: Ana", quantity=2, line_id=None):
        value = {"id": product, "name": "Caneca Personalizada", "quantity": quantity,
                 "note": note, "image": f"https://example.invalid/caneca-{index}.png"}
        if line_id is not None:
            value["lineId"] = line_id
        return value

    def test_legacy_migration_keeps_each_row_and_identity_survives_reload(self):
        legacy = [self.item(note="Nome: Ana", quantity=3), self.item(2, note="Nome: Bia", quantity=7)]
        states = self.run_cart(legacy, [{"event": "show"}, {"event": "reload"}, {"event": "show"}])
        migrated = states[0]["items"]
        self.assertEqual([{k: v for k, v in i.items() if k != "lineId"} for i in migrated], legacy)
        self.assertEqual(len({i["lineId"] for i in migrated}), 2)
        self.assertEqual(states[2]["items"], migrated)
        self.assertEqual(states[-1]["count"], "10")
        self.assertIn("2 itens/personalizações", states[-1]["total"])
        self.assertNotIn("produtos diferentes", states[-1]["total"])

    def test_duplicate_or_unsafe_line_ids_are_repaired_without_merging(self):
        saved = [self.item(line_id="afq-1"), self.item(2, line_id="afq-1", note="Bia"),
                 self.item(3, line_id='x\" onclick=\"alert(1)', note="Carla"), self.item(4, line_id="afq-2", note="Dora")]
        states = self.run_cart(saved, [{"event": "show"}, {"event": "reload"}])
        migrated = states[0]["items"]
        self.assertEqual([i["note"] for i in migrated], [i["note"] for i in saved])
        self.assertEqual(len({i["lineId"] for i in migrated}), 4)
        self.assertEqual(migrated[0]["lineId"], "afq-1")
        self.assertEqual(migrated[3]["lineId"], "afq-2")
        self.assertTrue(all(re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", i["lineId"]) for i in migrated))
        self.assertEqual(states[-1]["items"], migrated)

    def test_another_personalization_starts_empty_and_edits_only_its_row(self):
        states = self.run_cart([self.item(quantity=4, line_id="original")], [
            {"event": "show"}, {"event": "another", "row": 0},
            {"event": "note", "row": 1, "value": "Nome: Bia\nCor: rosa"},
            {"event": "quantity", "row": 1, "value": "3"}, {"event": "reload"}, {"event": "show"},
        ], mobile=True)
        original, fresh = states[2]["items"]
        self.assertEqual(original, self.item(quantity=4, line_id="original"))
        self.assertNotEqual(original["lineId"], fresh["lineId"])
        self.assertEqual((fresh["id"], fresh["quantity"], fresh["note"]), (original["id"], 1, ""))
        self.assertEqual(states[2]["focused"], "afquote-note-" + fresh["lineId"])
        self.assertTrue(states[2]["scrolled"])
        self.assertEqual(states[-1]["items"][0], original)
        self.assertEqual(states[-1]["items"][1]["note"], "Nome: Bia\nCor: rosa")
        self.assertEqual(states[-1]["items"][1]["quantity"], 3)
        self.assertEqual(states[-1]["count"], "7")

    def test_remove_and_stale_event_never_touch_a_different_row(self):
        items = [self.item(line_id="ana", quantity=2), self.item(2, line_id="bia", quantity=3), self.item(3, line_id="carla", quantity=5)]
        states = self.run_cart(items, [{"event": "show"}, {"event": "remove", "row": 1},
                                     {"event": "stale-remove", "lineId": "bia"}, {"event": "remove", "row": 1},
                                     {"event": "remove", "row": 0}])
        self.assertEqual([i["lineId"] for i in states[2]["items"]], ["ana", "carla"])
        self.assertEqual(states[2]["count"], "7")
        self.assertEqual(states[3]["items"], states[2]["items"])
        self.assertEqual(states[4]["count"], "2")
        self.assertEqual(states[-1]["items"], [])
        self.assertEqual(states[-1]["count"], "0")
        self.assertTrue(states[-1]["reviewDisabled"])
        self.assertTrue(states[-1]["clearDisabled"])
        self.assertEqual(states[-1]["focused"], "afquote-continue")

    def test_twenty_five_limit_counts_lines_even_for_one_product(self):
        items = [self.item(i, note=f"Nome {i}", quantity=1, line_id=f"line-{i}") for i in range(24)]
        states = self.run_cart(items, [{"event": "show"}, {"event": "another", "row": 23},
            {"event": "another", "row": 0}, {"event": "force-another", "lineId": "line-0"},
            {"event": "open", "product": "chaveiro-personalizado"}, {"event": "add"},
            {"event": "remove", "row": 24}, {"event": "another", "row": 0}])
        self.assertEqual(len(states[2]["items"]), 25)
        self.assertTrue(all(r["anotherDisabled"] for r in states[2]["rows"]))
        self.assertIn("25 itens/personalizações", states[2]["notice"])
        for index in (3, 4, 6):
            self.assertEqual(states[index]["items"], states[2]["items"])
        self.assertEqual(len(states[7]["items"]), 24)
        self.assertTrue(all(not r["anotherDisabled"] for r in states[7]["rows"]))
        self.assertEqual(len(states[-1]["items"]), 25)
        self.assertEqual(states[-1]["count"], "25")

    def test_saved_rows_above_limit_are_not_silently_discarded(self):
        items = [self.item(i, note=f"Observação {i}", quantity=1) for i in range(26)]
        state = self.run_cart(items, [{"event": "show"}])[-1]
        self.assertEqual(len(state["items"]), 26)
        self.assertEqual([i["note"] for i in state["items"]], [i["note"] for i in items])
        self.assertTrue(all(r["anotherDisabled"] for r in state["rows"]))
        self.assertIn("Limite de 25", state["notice"])

    def test_quantity_limit_rejects_bad_value_and_keeps_previous_quantity(self):
        for value in ("1000", "0", "-1", "2.5", "", "NaN"):
            with self.subTest(value=value):
                state = self.run_cart([self.item(quantity=5)], [{"event": "show"},
                                       {"event": "quantity", "value": value}])[-1]
                self.assertEqual(state["items"][0]["quantity"], 5)
                self.assertEqual(state["rows"][0]["quantity"], "5")
                self.assertEqual(state["count"], "5")
                self.assertIn("de 1 a 999", state["notice"])
        state = self.run_cart([self.item(quantity=5)], [{"event": "show"},
                               {"event": "quantity", "value": "999"}])[-1]
        self.assertEqual(state["items"][0]["quantity"], 999)
        self.assertEqual(state["count"], "999")

    def test_detail_add_with_one_or_many_existing_rows_changes_no_quantity(self):
        for count in (1, 3):
            with self.subTest(count=count):
                items = [self.item(i, quantity=i+2, note=f"Nome {i}", line_id=f"saved-{i}") for i in range(count)]
                state = self.run_cart(items, [{"event": "open", "product": "caneca-personalizada"},
                                              {"event": "add"}])[-1]
                self.assertEqual(state["items"], items)
                self.assertFalse(state["hidden"])
                self.assertIn("Outra personalização", state["notice"])
                self.assertIn("Nenhuma quantidade foi alterada", state["notice"])

    def test_real_detail_uses_product_id_with_equal_names_and_no_gallery(self):
        states = self.run_cart([], [{"event": "open", "product": "produto-b"}, {"event": "add"},
                                   {"event": "open", "product": "produto-a"}, {"event": "add"}],
            cardOverrides=[{"product": "produto-a", "detailName": "Mesmo nome"},
                           {"product": "produto-b", "detailName": "Mesmo nome"}])
        self.assertEqual(states[2]["items"][0]["id"], "produto-b")
        self.assertIn("chaveiro", states[2]["items"][0]["image"])
        self.assertEqual([i["id"] for i in states[-1]["items"]], ["produto-b", "produto-a"])

    def test_related_keyboard_and_deep_links_keep_the_actual_product(self):
        for gallery in (False, True):
            with self.subTest(gallery=gallery):
                states = self.run_cart([], [{"event": "add"}, {"event": "continue"},
                    {"event": "enter", "product": "caneca-personalizada"},
                    {"event": "related", "index": 0}, {"event": "add"}],
                    query="?produto=caneca-personalizada", gallery=gallery, mobile=True)
                self.assertEqual(states[0]["product"], "caneca-personalizada")
                self.assertEqual(states[1]["items"][0]["id"], "caneca-personalizada")
                self.assertTrue(states[2]["modalHidden"])
                self.assertEqual(states[4]["product"], "chaveiro-personalizado")
                self.assertEqual([i["id"] for i in states[-1]["items"]], ["caneca-personalizada", "chaveiro-personalizado"])
        states = self.run_cart([], [{"event": "dom-ready"}, {"event": "add"}],
                               query="?produto=chaveiro-personalizado", readyState="loading")
        self.assertEqual(states[-1]["items"][0]["id"], "chaveiro-personalizado")

    def test_slug_collision_in_actual_generated_catalog_never_selects_first_product(self):
        catalog = deepcopy(CATALOG)
        catalog[0]["Nome"] = "Caneca A"
        catalog[1]["Nome"] = "Caneca Á"
        page = fixture_page(catalog=catalog)
        self.assertEqual(page.count('data-product="caneca-a"'), 2)
        state = self.run_cart([], [{"event": "open", "product": "caneca-a"},
                                   {"event": "add"}], catalog=catalog)[-1]
        self.assertEqual(state["items"], [])
        self.assertIn("identificação repetida", state["alerts"][0])
        self.assertIn("Pedir orçamento deste produto", state["alerts"][0])

    def test_missing_detail_identity_never_falls_back_to_product_name(self):
        state = self.run_cart([], [{"event": "open", "product": "caneca-personalizada"},
                                  {"event": "missing-id"}, {"event": "add"}])[-1]
        self.assertEqual(state["items"], [])
        self.assertEqual(len(state["alerts"]), 1)
        self.assertIn("Abra novamente", state["alerts"][0])

    def test_text_escaping_keeps_names_and_notes_literal_in_dom_and_message(self):
        item = self.item(note='</textarea><img src=x onerror="alert(1)"> & "Azul"', line_id="safe")
        item["name"] = '<script>alert("nome")</script> & Caneca'
        item["image"] = 'https://example.invalid/x" onload="alert(1)'
        states = self.run_cart([item], [{"event": "show"}, {"event": "another"}, {"event": "review"}])
        html = states[1]["html"]
        self.assertNotIn('<script>alert', html)
        self.assertNotIn('</textarea><img src=x', html)
        self.assertIn('&lt;/textarea&gt;', html)
        self.assertIn('x&quot; onload=&quot;', html)
        self.assertEqual(states[1]["rows"][0]["note"], item["note"])
        self.assertEqual(states[2]["items"][0], item)
        self.assertIn(item["name"], states[-1]["message"])
        self.assertIn(item["note"], states[-1]["message"])

    def test_actual_ui_message_reaches_hf54_as_two_personalizations(self):
        states = self.run_cart([], [{"event": "open", "product": "caneca-personalizada"}, {"event": "add"},
            {"event": "quantity", "row": 0, "value": "2"}, {"event": "note", "row": 0, "value": "Nome: Ana\nCor: azul"},
            {"event": "another", "row": 0}, {"event": "quantity", "row": 1, "value": "3"},
            {"event": "note", "row": 1, "value": "Nome: Bia\nCor: rosa"},
            {"event": "review"}, {"event": "copy"}, {"event": "send"}])
        final = states[-1]
        self.assertEqual(final["message"].count("Caneca Personalizada"), 2)
        self.assertIn("1. Caneca Personalizada\nQuantidade: 2", final["message"])
        self.assertIn("2. Caneca Personalizada\nQuantidade: 3", final["message"])
        analysis = analisar_mensagem(final["message"], CATALOG)
        self.assertFalse(analysis["erros"])
        draft = preparar_rascunho(analysis, deepcopy(analysis["itens"]))
        self.assertEqual([i["produto_catalogo_id"] for i in draft["itens"]], ["CAT-01", "CAT-01"])
        self.assertEqual([i["quantidade"] for i in draft["itens"]], [2, 3])
        self.assertEqual([i["especificacoes"] for i in draft["itens"]], ["Nome: Ana\nCor: azul", "Nome: Bia\nCor: rosa"])
        self.assertEqual(final["copied"], [final["message"]])
        self.assertEqual(len(final["opened"]), 1)
        self.assertEqual(final["metrics"][0]["context"], "carrinho")
        self.assertEqual(final["metrics"][0]["product"], "Orçamento com 2 itens/personalizações")


if __name__ == "__main__":
    unittest.main()
