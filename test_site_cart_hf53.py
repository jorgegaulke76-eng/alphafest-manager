"""Fluxos de orçamento curto/longo e cópia integral, executados offline."""
import json
import re
import shutil
import subprocess
import unittest
from urllib.parse import parse_qs, urlsplit

from site_carrinho_orcamento_service import inject_cart


_CART_RUNNER = r'''
(async function(){
const vm=require('vm'),input=JSON.parse(require('fs').readFileSync(0,'utf8'));
const ids={},opened=[],copied=[],metrics=[],alerts=[];
function node(id=''){
  const value={id,dataset:{},hidden:false,disabled:false,value:'',textContent:'',innerHTML:'',listeners:{},
    setAttribute(){},appendChild(child){if(child.id)ids[child.id]=child;},
    querySelector(selector){return get(selector.replace(/^[#.]/,''));},
    querySelectorAll(selector){
      if(selector==='[data-afquote-close]')return [get('afquote-close')];
      if(selector==='.afquote-continue')return [get('afquote-continue'),get('afquote-continue-review')];
      return [];
    },
    addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);},
    async fire(type,event={}){for(const fn of this.listeners[type]||[])await fn(event);},
    focus(){document.activeElement=this;},select(){this.selected=true;}
  };return value;
}
function get(id){return ids[id]||(ids[id]=node(id));}
const modal=get('product-detail-modal');modal.hidden=true;
const document=node();document.body=node();document.activeElement=node();
document.querySelector=()=>({dataset:{detailName:'Produto teste'}});
document.querySelectorAll=()=>[];
document.getElementById=get;
document.createElement=()=>node();
document.execCommand=()=>{if(input.clipboard==='fallback'){copied.push(get('afquote-message').value);return true;}return false;};
const storage=new Map([['alphafest_orcamento_hf652423',JSON.stringify(input.items)]]);
const localStorage={getItem:key=>storage.get(key)??null,setItem(key,value){storage.set(key,value);}};
const navigator={clipboard:{async writeText(text){if(input.clipboard==='manual'||input.clipboard==='fallback')throw new Error('Sem permissão');copied.push(text);}}};
const window={location:{href:''},dispatchEvent(event){metrics.push(event.detail);},open(url){opened.push(url);return {};}};
class CustomEvent{constructor(type,options){this.type=type;this.detail=options.detail;}}
vm.runInNewContext(input.script,{document,window,navigator,localStorage,CustomEvent,alert:m=>alerts.push(m),confirm:()=>true},{timeout:1000});
function state(){return {message:get('afquote-message').value,helpHidden:get('afquote-message-help').hidden,
  sendLabel:get('afquote-send').textContent,sendDisabled:get('afquote-send').disabled,
  copyStatus:get('afquote-copy-status').textContent,selected:!!get('afquote-message').selected,
  opened:[...opened],copied:[...copied],metrics:[...metrics],alerts:[...alerts]};}
const states=[state()];
for(const action of input.actions){
  if(action.event==='edit'){get('afquote-message').value=action.text;await get('afquote-message').fire('input');}
  else await get('afquote-'+action.event).fire('click');
  states.push(state());
}
process.stdout.write(JSON.stringify(states));
})().catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
'''


class SiteCartHF53Tests(unittest.TestCase):
    def run_cart(self, items, actions, *, clipboard="success", number="11999991234"):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node local necessário para executar a revisão do orçamento")
        page = inject_cart('<html><head></head><body><article class="product-card" data-detail-name="Teste"></article><div id="product-detail-modal"></div></body></html>', {"celular": number})
        script = re.search(r'<script id="afquote-js">(.*?)</script>', page, re.S)[1]
        result = subprocess.run([node, "-e", _CART_RUNNER], input=json.dumps({
            "script": script, "items": items, "actions": actions, "clipboard": clipboard,
        }), text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def item(self, index, note=""):
        return {"id": f"p{index}", "name": f"Produto {index:02d}", "quantity": index,
                "note": note, "image": ""}

    def test_all_25_items_and_notes_reach_review_and_clipboard(self):
        items = [self.item(i, f"Observação {i:02d}: ".ljust(450, "x")) for i in range(1, 26)]
        states = self.run_cart(items, [{"event": "review"}, {"event": "copy"}, {"event": "send"}])
        review = states[1]
        self.assertGreater(len(review["message"]), 6000)
        for item in items:
            self.assertIn(item["name"], review["message"])
            self.assertIn(item["note"], review["message"])
        self.assertIn("opções de retirada/entrega", review["message"])
        self.assertFalse(review["helpHidden"])
        self.assertEqual(review["opened"], [])
        self.assertEqual(states[2]["copied"], [review["message"]])
        self.assertEqual(states[2]["opened"], [])
        self.assertEqual(states[3]["opened"], ["https://wa.me/5511999991234"])
        self.assertEqual(len(states[3]["metrics"]), 1)

    def test_short_message_preserves_prefilled_manual_whatsapp(self):
        states = self.run_cart([self.item(1, "Azul, nome João")], [{"event": "review"}, {"event": "send"}])
        self.assertTrue(states[1]["helpHidden"])
        self.assertEqual(states[1]["opened"], [])
        url = states[2]["opened"][0]
        self.assertLessEqual(len(url), 3500)
        self.assertEqual(parse_qs(urlsplit(url).query)["text"], [states[1]["message"]])

    def test_edited_message_is_kept_and_reclassified_by_url_length(self):
        states = self.run_cart([self.item(1)], [
            {"event": "review"}, {"event": "edit", "text": "🎈" * 350},
            {"event": "copy"}, {"event": "send"},
            {"event": "edit", "text": "Texto final ajustado pelo cliente"}, {"event": "send"},
        ])
        self.assertLess(len(states[2]["message"]), 6000)
        self.assertFalse(states[2]["helpHidden"])
        self.assertEqual(states[3]["copied"], ["🎈" * 350])
        self.assertNotIn("?", states[4]["opened"][0])
        self.assertTrue(states[5]["helpHidden"])
        self.assertEqual(parse_qs(urlsplit(states[6]["opened"][-1]).query)["text"], ["Texto final ajustado pelo cliente"])

    def test_clipboard_failure_has_complete_manual_selection_fallback(self):
        states = self.run_cart([self.item(1, "Observação importante")], [{"event": "review"}, {"event": "copy"}], clipboard="manual")
        self.assertEqual(states[2]["message"], states[1]["message"])
        self.assertTrue(states[2]["selected"])
        self.assertIn("Use a opção Copiar", states[2]["copyStatus"])
        self.assertEqual(states[2]["opened"], [])
        self.assertEqual(states[2]["metrics"], [])

    def test_legacy_clipboard_fallback_copies_whole_message(self):
        states = self.run_cart([self.item(1)], [{"event": "review"}, {"event": "copy"}], clipboard="fallback")
        self.assertEqual(states[-1]["copied"], [states[1]["message"]])
        self.assertIn("Mensagem completa copiada", states[-1]["copyStatus"])

    def test_empty_message_and_missing_number_do_not_open_whatsapp(self):
        states = self.run_cart([self.item(1)], [{"event": "review"}, {"event": "edit", "text": " "}, {"event": "send"}])
        self.assertTrue(states[-1]["sendDisabled"])
        self.assertEqual(states[-1]["opened"], [])
        states = self.run_cart([self.item(1)], [{"event": "review"}, {"event": "send"}], number="")
        self.assertEqual(states[-1]["opened"], [])
        self.assertEqual(len(states[-1]["alerts"]), 1)


if __name__ == "__main__":
    unittest.main()
