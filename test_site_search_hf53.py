"""Busca por temas e recuperação de filtros sem resultado, sem rede."""
from html.parser import HTMLParser
import json
import re
import shutil
import subprocess
import unittest
from urllib.parse import parse_qs, urlsplit

from site_vitrine_service import gerar_html_vitrine


class _SearchDOM(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards, self.buttons, self.subbuttons, self.ids = [], [], [], {}
        self.button = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids[attrs["id"]] = attrs
        classes = attrs.get("class", "").split()
        if tag == "article" and "product-card" in classes:
            self.cards.append(attrs)
        if tag == "button" and ("filter" in classes or "subfilter" in classes):
            self.button = {"attrs": attrs, "text": ""}
            (self.subbuttons if "subfilter" in classes else self.buttons).append(self.button)

    def handle_data(self, data):
        if self.button is not None:
            self.button["text"] += data

    def handle_endtag(self, tag):
        if tag == "button":
            self.button = None


_SEARCH_RUNNER = r'''
const vm=require('vm'),input=JSON.parse(require('fs').readFileSync(0,'utf8'));
function element(attrs={},text=''){
  const classes=new Set((attrs.class||'').split(' '));
  const dataset={};for(const [key,value] of Object.entries(attrs))if(key.startsWith('data-'))dataset[key.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=value;
  return {dataset,textContent:text,innerHTML:'',value:'',style:{},hidden:'hidden' in attrs,href:attrs.href||'',listeners:{},
    classList:{contains(c){return classes.has(c);},add(c){classes.add(c);},remove(c){classes.delete(c);},toggle(c,state){if(state)classes.add(c);else classes.delete(c);}},
    addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);},
    fire(type,event={}){for(const fn of this.listeners[type]||[])fn(event);},
    click(){this.fire('click');},dispatchEvent(event){this.fire(event.type,event);},focus(){},scrollIntoView(){}
  };
}
const cards=input.cards.map(attrs=>element(attrs)),buttons=input.buttons.map(b=>element(b.attrs,b.text)),subs=input.subbuttons.map(b=>element(b.attrs,b.text));
const ids=Object.fromEntries(Object.entries(input.ids).map(([id,attrs])=>[id,element(attrs)]));
const document={getElementById:id=>ids[id]||null,
  querySelectorAll(selector){return selector==='.product-card'?cards:selector==='.filter'?buttons:selector==='.subfilter'?subs:[];},
  querySelector(selector){
    if(selector==='.filter.active')return buttons.find(b=>b.classList.contains('active'))||null;
    if(selector==='.subfilter.active')return subs.find(b=>b.classList.contains('active'))||null;
    if(selector==='.filter[data-cat="todos"]')return buttons.find(b=>b.dataset.cat==='todos')||null;
    return null;
  }
};
class Event{constructor(type,options){this.type=type;this.bubbles=options?.bubbles;}}
vm.runInNewContext(input.script,{document,window:{innerWidth:390},Event},{timeout:1000});
function state(){return {products:cards.filter(c=>c.style.display!=='none').map(c=>c.dataset.product),
  count:ids['result-count'].textContent,query:ids.search.value,
  hidden:ids['search-feedback'].hidden,feedback:ids['search-feedback-text'].textContent,
  contact:ids['search-feedback-contact']?.href||'',
  category:buttons.find(b=>b.classList.contains('active'))?.dataset.cat||''};}
const states=[state()];
for(const action of input.actions){
  if(action.event==='query'){ids.search.value=action.text;ids.search.fire('input');}
  if(action.event==='category')buttons.find(b=>b.dataset.cat===action.slug).click();
  if(action.event==='reset')ids['search-feedback-clear'].click();
  states.push(state());
}
process.stdout.write(JSON.stringify(states));
'''


class SiteSearchHF53Tests(unittest.TestCase):
    def page(self, taxonomy=True, phone="11999991234"):
        products = [
            {"Nome": "Painel infantil", "DescricaoCompleta": "Peça decorativa para festa.",
             "Categoria": "PAPELARIA", "Subcategoria": "PAINÉIS", "Temas": ["Astronauta"],
             "Imagens": ["https://example.invalid/painel.png"], "PublicarSite": True},
            {"Nome": "Caneca cerâmica", "DescricaoCompleta": "Caneca para presentear.",
             "Categoria": "PERSONALIZADOS", "Subcategoria": "CANECAS", "Aliases": ["mug"],
             "Imagens": ["https://example.invalid/caneca.png"], "PublicarSite": True},
        ]
        return gerar_html_vitrine(products, {"celular": phone}, usar_taxonomia_catalogo=taxonomy, modo_preview=False)

    def run_search(self, actions, *, taxonomy=True, phone="11999991234"):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node local necessário para testar os filtros emitidos")
        page = self.page(taxonomy, phone)
        dom = _SearchDOM()
        dom.feed(page)
        script = re.findall(r'<script[^>]*>(.*?)</script>', page, re.S)[0]
        result = subprocess.run([node, "-e", _SEARCH_RUNNER], input=json.dumps({
            "script": script, "cards": dom.cards, "buttons": dom.buttons,
            "subbuttons": dom.subbuttons, "ids": dom.ids, "actions": actions,
        }), text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_existing_theme_alias_and_typo_tolerance_work_in_both_modes(self):
        for taxonomy in (True, False):
            with self.subTest(taxonomy=taxonomy):
                states = self.run_search([
                    {"event": "query", "text": "Astronauta"},
                    {"event": "query", "text": "mug"},
                    {"event": "query", "text": "caneca seramica"},
                ], taxonomy=taxonomy)
                self.assertEqual(states[1]["products"], ["painel-infantil"])
                self.assertEqual(states[2]["products"], ["caneca-ceramica"])
                self.assertEqual(states[3]["products"], ["caneca-ceramica"])
                self.assertTrue(states[3]["hidden"])

    def test_no_results_has_contextual_consultation_and_clears_all_filters(self):
        states = self.run_search([
            {"event": "category", "slug": "personalizados"},
            {"event": "query", "text": "Astronauta"},
            {"event": "reset"},
        ])
        empty = states[2]
        self.assertEqual(empty["products"], [])
        self.assertFalse(empty["hidden"])
        message = parse_qs(urlsplit(empty["contact"]).query)["text"][0]
        self.assertIn("Astronauta", message)
        self.assertIn("Categoria: PERSONALIZADOS", message)
        self.assertIn("opções sob encomenda", message)
        self.assertEqual(states[3]["category"], "todos")
        self.assertEqual(states[3]["query"], "")
        self.assertEqual(len(states[3]["products"]), 2)
        self.assertTrue(states[3]["hidden"])

    def test_plain_text_query_is_preserved_without_inserting_html(self):
        query = '<img src=x onerror="alert(1)"> pedido único'
        for taxonomy in (True, False):
            with self.subTest(taxonomy=taxonomy):
                states = self.run_search([{"event": "query", "text": query}, {"event": "reset"}], taxonomy=taxonomy)
                self.assertIn(query, states[1]["feedback"])
                self.assertIn(query, parse_qs(urlsplit(states[1]["contact"]).query)["text"][0])
                self.assertEqual(len(states[2]["products"]), 2)
                self.assertTrue(states[2]["hidden"])

    def test_missing_whatsapp_does_not_create_an_invalid_contact_url(self):
        states = self.run_search([{"event": "query", "text": "xyzxyzxyz"}, {"event": "reset"}], phone="")
        self.assertEqual(states[1]["contact"], "")
        self.assertFalse(states[1]["hidden"])
        self.assertEqual(len(states[2]["products"]), 2)


if __name__ == "__main__":
    unittest.main()
