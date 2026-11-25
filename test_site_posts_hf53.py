"""Validade comercial e navegação de ofertas em HTML estático, sem rede."""
from datetime import date, datetime, timezone
from html.parser import HTMLParser
import json
import re
import shutil
import subprocess
import unittest
from unittest.mock import patch

from site_posts_service import _commercial_today, archive_pages, inject_home, published


def post(index, expiry="", status="publicado"):
    return {"id": str(index), "title": f"Arte {index}", "status": status,
            "image_data_uri": "data:image/png;base64,AA==", "expires_at": expiry,
            "created_at": "2026-11-25", "featured": False}


class _PostAttrs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "article" and "afposts-card" in values.get("class", "").split():
            self.cards.append({"expiry": values.get("data-afpost-expires", ""),
                               "hidden": "hidden" in values})


_EXPIRY_RUNNER = r'''
const vm=require('vm'),input=JSON.parse(require('fs').readFileSync(0,'utf8'));
let currentTime=input.now;
class ClockDate extends Date{constructor(...args){super(...(args.length?args:[currentTime]));}static now(){return new Date(currentTime).getTime();}}
function target(){return {listeners:{},addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);},fire(name,event={}){for(const fn of this.listeners[name]||[])fn(event);}};}
const cards=input.cards.map(c=>({hidden:c.hidden,dataset:{afpostExpires:c.expiry},closest(){return c.expiry?this:null;}}));
const empty={hidden:true};
const scope={querySelectorAll:()=>cards,querySelector:()=>empty};
const document=target();document.querySelectorAll=()=>[scope];
const window=target(),timers=[];window.setInterval=fn=>{timers.push(fn);return timers.length;};
const international=input.failIntl?{DateTimeFormat(){throw new Error('Intl indisponível');}}:Intl;
vm.runInNewContext(input.script,{document,window,Date:ClockDate,Intl:international},{timeout:1000});
let prevented=0;
const state=()=>({hidden:cards.map(c=>c.hidden),empty:empty.hidden,prevented});
const states=[state()];
for(const action of input.actions){
  if(action.now)currentTime=action.now;
  if(action.event==='tick')timers.forEach(fn=>fn());
  if(action.event==='visibilitychange')document.fire('visibilitychange');
  if(action.event==='pageshow'||action.event==='focus')window.fire(action.event);
  if(action.event==='click'||action.event==='auxclick')document.fire(action.event,{
    target:cards[action.index||0],preventDefault(){prevented++;},stopImmediatePropagation(){}
  });
  states.push(state());
}
process.stdout.write(JSON.stringify(states));
'''


class SitePostsHF53Tests(unittest.TestCase):
    def generated(self, entries):
        with patch("site_posts_service._commercial_today", return_value=date(2026, 11, 30)):
            home = inject_home('<html><head></head><body><footer class="footer"></footer></body></html>', entries, "11999991234")
            pages = archive_pages(entries, "11999991234")
        return home, pages

    def run_expiry(self, page, *, now="2026-12-01T02:59:59Z", actions=(), fail_intl=False):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node local necessário para testar o JavaScript publicado")
        attrs = _PostAttrs()
        attrs.feed(page)
        script = re.search(r'<script id="afposts-expiry-hf53">(.*?)</script>', page, re.S)[1]
        result = subprocess.run([node, "-e", _EXPIRY_RUNNER], input=json.dumps({
            "script": script, "cards": attrs.cards, "now": now,
            "actions": actions, "failIntl": fail_intl,
        }), text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_build_uses_sao_paulo_day_and_inclusive_expiry(self):
        before = datetime(2026, 12, 1, 2, 59, 59, tzinfo=timezone.utc)
        after = datetime(2026, 12, 1, 3, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(_commercial_today(before), date(2026, 11, 30))
        self.assertEqual(_commercial_today(after), date(2026, 12, 1))
        entries = [post(1, "2026-11-30"), post(2), post(3, "2026-02-31"), post(4, status="rascunho")]
        self.assertEqual({p["id"] for p in published(entries, date(2026, 11, 30))}, {"1", "2"})
        self.assertEqual({p["id"] for p in published(entries, date(2026, 12, 1))}, {"2"})

    def test_previous_and_next_cover_all_four_static_pages(self):
        _, pages = self.generated([post(i) for i in range(73)])
        self.assertEqual(len(pages), 4)
        self.assertNotIn("← Anterior", pages["novidades/index.html"])
        for page in (2, 3, 4):
            expected = "/novidades/" if page == 2 else f"/novidades/pagina-{page-1}/"
            html = pages[f"novidades/pagina-{page}/index.html"]
            self.assertIn(f'href="{expected}">← Anterior', html)
            if page < 4:
                self.assertIn(f'href="/novidades/pagina-{page+1}/">Próxima', html)
        self.assertNotIn("Próxima →", pages["novidades/pagina-4/index.html"])

    def test_home_and_archive_hide_expired_cards_after_midnight(self):
        home, pages = self.generated([post(1, "2026-11-30"), post(2)])
        for page in (home, pages["novidades/index.html"]):
            with self.subTest(home=page is home):
                attrs = _PostAttrs()
                attrs.feed(page)
                dated = next(i for i, card in enumerate(attrs.cards) if card["expiry"])
                permanent = next(i for i, card in enumerate(attrs.cards) if not card["expiry"])
                self.assertTrue(attrs.cards[dated]["hidden"])
                states = self.run_expiry(page, actions=[{"now": "2026-12-01T03:00:00Z", "event": "tick"}])
                self.assertFalse(states[0]["hidden"][dated])
                self.assertTrue(states[1]["hidden"][dated])
                self.assertFalse(states[1]["hidden"][permanent])
                self.assertTrue(states[1]["empty"])

    def test_expired_click_is_blocked_even_before_periodic_refresh(self):
        home, _ = self.generated([post(1, "2026-11-30")])
        for event in ("click", "auxclick"):
            with self.subTest(event=event):
                states = self.run_expiry(home, actions=[{"now": "2026-12-01T03:00:00Z", "event": event}])
                self.assertEqual(states[-1]["prevented"], 1)
                self.assertEqual(states[-1]["hidden"], [True])
                self.assertFalse(states[-1]["empty"])

    def test_returning_to_a_stale_page_refreshes_validity(self):
        home, pages = self.generated([post(1, "2026-11-30")])
        for event in ("pageshow", "focus", "visibilitychange"):
            with self.subTest(event=event):
                states = self.run_expiry(pages["novidades/index.html"], actions=[{"now": "2026-12-01T03:00:00Z", "event": event}])
                self.assertEqual(states[-1]["hidden"], [True])
                self.assertFalse(states[-1]["empty"])

    def test_date_limited_offers_stay_hidden_if_timezone_cannot_be_checked(self):
        home, _ = self.generated([post(1, "2026-11-30"), post(2)])
        state = self.run_expiry(home, fail_intl=True)[0]
        self.assertEqual(sorted(state["hidden"]), [False, True])
        self.assertTrue(state["empty"])

    def test_expiry_injection_is_idempotent_and_preserves_no_draft_rule(self):
        home, pages = self.generated([post(1), post(2, status="rascunho")])
        self.assertEqual(inject_home(home, [post(1)]), home)
        self.assertEqual(home.count('id="afposts-expiry-hf53"'), 1)
        self.assertNotIn("Arte 2", home)
        self.assertNotIn("Arte 2", pages["novidades/index.html"])


if __name__ == "__main__":
    unittest.main()
