"""Regressão offline da ficha HF65.24.52, sem app, banco ou navegador externo.

Executar com: python -m unittest test_site_vitrine_hf52 -v
Os testes de comportamento usam somente o runtime JavaScript local (Node).
"""
from __future__ import annotations

import copy
from html.parser import HTMLParser
import json
import re
import shutil
import subprocess
import unittest

from site_vitrine_service import gerar_html_vitrine


class _Cards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "product-card" in attrs.get("class", "").split():
            self.cards.append({
                re.sub(r"-([a-z])", lambda m: m[1].upper(), key[5:]): value
                for key, value in attrs.items() if key.startswith("data-")
            })


# DOM mínimo para executar o script realmente emitido pelo gerador. Não fornece
# APIs de rede e observa somente abertura, foco, links e dimensões da ficha.
_MODAL_RUNNER = r'''
const vm=require('vm');
const input=JSON.parse(require('fs').readFileSync(0,'utf8'));
function element(dataset={}){
  return {dataset,hidden:false,textContent:'',innerHTML:'',children:[],listeners:{},
    style:{removeProperty(key){delete this[key];}},
    setAttribute(key,value){this[key]=value;},removeAttribute(key){delete this[key];},
    addEventListener(name,fn,options={}){(this.listeners[name]??=[]).push({fn,once:!!options.once});},
    fire(name,event={}){
      if(!event.target)event.target=this;
      for(const listener of [...(this.listeners[name]||[])]){
        if(listener.once)this.listeners[name]=this.listeners[name].filter(x=>x!==listener);
        listener.fn(event);
      }
      if(name==='click'&&this.parent)this.parent.fire(name,event);
    },
    click(){this.fire('click');},
    appendChild(child){this.children.push(child);},
    focus(options){this.focusOptions=options??null;this.focused=true;this.focusCount=(this.focusCount||0)+1;},
    scrollIntoView(){this.scrolled=true;}
  };
}
const ids={};
for(const id of ['product-detail-modal','product-detail-name','product-detail-description',
  'product-detail-tax','product-detail-price','product-detail-image','product-detail-placeholder',
  'product-detail-whatsapp','product-detail-gallery','product-related','product-related-grid'])ids[id]=element();
const modal=ids['product-detail-modal'];modal.hidden=true;
const close=element(),backdrop=element();
modal.querySelector=()=>close;
modal.querySelectorAll=()=>[close,backdrop];
const cards=input.cards.map(element);
const classes=new Set();
const document=element();
document.readyState=input.readyState;
cards.forEach(card=>card.parent=document);
document.getElementById=id=>ids[id]||null;
document.querySelectorAll=()=>cards;
document.createElement=()=>element();
document.body={classList:{add(x){classes.add(x);},remove(x){classes.delete(x);}}};
const window=element();
window.location={search:input.query};
let mobile=input.mobile;
window.matchMedia=()=>({matches:mobile});
if(!input.noViewport)window.visualViewport=Object.assign(element(),{offsetLeft:12,offsetTop:18,width:390,height:720});
const observedClicks=[];
function installClickObserver(){document.addEventListener('click',event=>{
  if(event.target.dataset.product)observedClicks.push(event.target.dataset.product);
});}
if(input.observeBefore)installClickObserver();
const context=vm.createContext({window,document,URLSearchParams});
vm.runInContext(input.script,context,{timeout:1000});
function state(){
  const style={};for(const p of ['left','top','width','height','right','bottom'])
    if(modal.style[p]!==undefined)style[p]=modal.style[p];
  return {hidden:modal.hidden,name:ids['product-detail-name'].textContent,
    description:ids['product-detail-description'].textContent,
    whatsapp:ids['product-detail-whatsapp'].href||'',style,
    locked:classes.has('product-modal-open'),focus:close.focusOptions,
    openings:close.focusCount||0,observedClicks:[...observedClicks],
    focusedCards:cards.filter(c=>c.focused).map(c=>c.dataset.product),
    galleryProduct:ids['product-detail-gallery'].dataset.galleryProduct||''};
}
const states=[state()];
for(const action of input.actions){
  if('mobile' in action)mobile=action.mobile;
  if(action.event==='install-click-observer')installClickObserver();
  if(action.event==='dom-ready'){
    document.readyState='interactive';
    document.fire('DOMContentLoaded');
  }
  if(action.event==='window-resize')window.fire('resize');
  if(action.event==='viewport-resize'){
    Object.assign(window.visualViewport,action.viewport||{});
    window.visualViewport.fire('resize');
  }
  if(action.event==='viewport-scroll'){
    Object.assign(window.visualViewport,action.viewport||{});
    window.visualViewport.fire('scroll');
  }
  if(action.event==='close')close.fire('click');
  if(action.event==='escape')document.fire('keydown',{key:'Escape'});
  if(action.event==='click')cards.find(c=>c.dataset.product===action.product).fire('click');
  if(action.event==='enter')cards.find(c=>c.dataset.product===action.product).fire('keydown',{key:'Enter',preventDefault(){}});
  states.push(state());
}
process.stdout.write(JSON.stringify(states));
'''


class SiteVitrineHF52Tests(unittest.TestCase):
    def setUp(self):
        self.catalogo = [
            {"Nome": 'Caneca "Teste" & Cia', "DescricaoCompleta": "Descrição <literal> de teste.",
             "Categoria": "PERSONALIZADOS", "Subcategoria": "CANECAS",
             "Imagens": ["https://example.invalid/caneca.png"],
             "PublicarSite": True, "Ativo": True},
            {"Nome": "Chaveiro Teste", "DescricaoCompleta": "Outro produto da mesma fonte.",
             "Categoria": "PERSONALIZADOS", "Subcategoria": "LEMBRANÇAS",
             "Imagens": ["https://example.invalid/chaveiro.png"],
             "PublicarSite": True, "Ativo": True},
            {"Nome": "Produto privado", "DescricaoCompleta": "Não deve aparecer.",
             "Categoria": "PERSONALIZADOS", "Imagens": ["https://example.invalid/privado.png"],
             "PublicarSite": False, "Ativo": True},
        ]
        self.empresa = {"nome": "Empresa de Teste", "celular": "11999991234"}

    def page(self, preview=False):
        return gerar_html_vitrine(
            self.catalogo, self.empresa, modo_preview=preview,
            usar_taxonomia_catalogo=True,
            produtos_com_galeria=['Caneca "Teste" & Cia'],
        )

    def run_modal(self, query="", *, preview=False, mobile=True, no_viewport=False,
                  ready_state="complete", observe_before=False, actions=()):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node local necessário para executar o JavaScript emitido")
        page = self.page(preview)
        parser = _Cards()
        parser.feed(page)
        script = next(code for code in re.findall(r"<script[^>]*>(.*?)</script>", page, re.S)
                      if "const modal=document.getElementById('product-detail-modal')" in code)
        payload = {"script": script, "cards": parser.cards, "query": query,
                   "mobile": mobile, "noViewport": no_viewport, "actions": actions,
                   "readyState": ready_state, "observeBefore": observe_before}
        result = subprocess.run(
            [node, "-e", _MODAL_RUNNER], input=json.dumps(payload), text=True,
            capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_preview_and_public_output_use_current_catalog_without_mutation(self):
        original = copy.deepcopy((self.catalogo, self.empresa))
        for preview in (True, False):
            with self.subTest(preview=preview):
                page = self.page(preview)
                parser = _Cards()
                parser.feed(page)
                self.assertEqual({c["product"] for c in parser.cards}, {"caneca-teste-cia", "chaveiro-teste"})
                self.assertIn("Empresa de Teste", page)
                self.assertIn("5511999991234", page)
                self.assertNotIn("Produto privado", page)
                self.assertNotIn('id="hf52-preview-warning"', page)
                self.assertNotIn("PRÉVIA ISOLADA", page)
                self.assertEqual('class="preview-bar"' in page, preview)
                self.assertIn('id="hf652452-product-mobile-css"', page)
        self.assertEqual((self.catalogo, self.empresa), original)

    def test_deep_link_opens_current_product_in_preview_and_public_output(self):
        for preview in (True, False):
            with self.subTest(preview=preview):
                state = self.run_modal("?produto=caneca-teste-cia", preview=preview)[0]
                self.assertFalse(state["hidden"])
                self.assertEqual(state["name"], 'Caneca "Teste" & Cia')
                self.assertEqual(state["description"], "Descrição <literal> de teste.")
                self.assertTrue(state["whatsapp"].startswith("https://wa.me/5511999991234?"))
                self.assertEqual(state["galleryProduct"], "caneca-teste-cia")
                self.assertEqual(state["focus"], {"preventScroll": True})
                self.assertTrue(state["locked"])
                self.assertEqual(state["style"]["width"], "390px")

    def test_unknown_private_invalid_or_absent_product_does_not_open_modal(self):
        for query in ("", "?produto=inexistente", "?produto=produto-privado", "?produto=%3Cimg%20onerror%3Dx%3E"):
            with self.subTest(query=query):
                state = self.run_modal(query)[0]
                self.assertTrue(state["hidden"])
                self.assertFalse(state["locked"])
                self.assertEqual(state["style"], {})

    def test_loading_waits_for_later_click_listeners_and_opens_exactly_once(self):
        states = self.run_modal("?produto=caneca-teste-cia", ready_state="loading", actions=[
            {"event": "install-click-observer"},
            {"event": "dom-ready"},
            {"event": "dom-ready"},
            {"event": "close"},
            {"event": "click", "product": "chaveiro-teste"},
        ])
        self.assertTrue(states[0]["hidden"])
        self.assertEqual(states[1]["openings"], 0)
        self.assertEqual(states[2]["observedClicks"], ["caneca-teste-cia"])
        self.assertEqual(states[2]["openings"], 1)
        self.assertEqual(states[3]["observedClicks"], ["caneca-teste-cia"])
        self.assertEqual(states[3]["openings"], 1)
        self.assertEqual(states[5]["observedClicks"], ["caneca-teste-cia", "chaveiro-teste"])
        self.assertEqual(states[5]["openings"], 2)

    def test_ready_document_uses_the_same_click_event_once(self):
        state = self.run_modal("?produto=caneca-teste-cia", observe_before=True)[0]
        self.assertFalse(state["hidden"])
        self.assertEqual(state["observedClicks"], ["caneca-teste-cia"])
        self.assertEqual(state["openings"], 1)

    def test_loading_invalid_private_and_unknown_products_emit_no_click(self):
        for query in ("", "?produto=inexistente", "?produto=produto-privado", "?produto=%3Cimg%20onerror%3Dx%3E"):
            with self.subTest(query=query):
                states = self.run_modal(query, ready_state="loading", actions=[
                    {"event": "install-click-observer"},
                    {"event": "dom-ready"},
                ])
                self.assertTrue(states[-1]["hidden"])
                self.assertEqual(states[-1]["observedClicks"], [])
                self.assertEqual(states[-1]["openings"], 0)

    def test_mobile_resize_and_scroll_follow_visual_viewport(self):
        states = self.run_modal("?produto=caneca-teste-cia", actions=[
            {"event": "viewport-resize", "viewport": {"width": 360, "height": 480}},
            {"event": "viewport-scroll", "viewport": {"offsetLeft": 4, "offsetTop": 30}},
        ])
        self.assertEqual(states[1]["style"]["width"], "360px")
        self.assertEqual(states[1]["style"]["height"], "480px")
        self.assertEqual(states[2]["style"]["left"], "4px")
        self.assertEqual(states[2]["style"]["top"], "30px")

    def test_rotation_to_desktop_clears_mobile_inline_dimensions(self):
        states = self.run_modal("?produto=caneca-teste-cia", actions=[
            {"event": "window-resize", "mobile": False},
            {"event": "viewport-resize", "mobile": True},
            {"event": "viewport-resize", "mobile": False},
        ])
        self.assertTrue(states[0]["style"])
        self.assertEqual(states[1]["style"], {})
        self.assertTrue(states[2]["style"])
        self.assertEqual(states[3]["style"], {})
        self.assertFalse(states[3]["hidden"])

    def test_close_then_open_another_product_and_escape(self):
        states = self.run_modal("?produto=caneca-teste-cia", actions=[
            {"event": "close"},
            {"event": "enter", "product": "chaveiro-teste"},
            {"event": "escape"},
        ])
        self.assertTrue(states[1]["hidden"])
        self.assertEqual(states[1]["style"], {})
        self.assertIn("caneca-teste-cia", states[1]["focusedCards"])
        self.assertFalse(states[2]["hidden"])
        self.assertEqual(states[2]["name"], "Chaveiro Teste")
        self.assertTrue(states[3]["hidden"])
        self.assertFalse(states[3]["locked"])

    def test_desktop_and_browser_without_visual_viewport_keep_standard_layout(self):
        for options in ({"mobile": False}, {"no_viewport": True}):
            with self.subTest(**options):
                state = self.run_modal("?produto=caneca-teste-cia", **options)[0]
                self.assertFalse(state["hidden"])
                self.assertEqual(state["style"], {})


if __name__ == "__main__":
    unittest.main()
