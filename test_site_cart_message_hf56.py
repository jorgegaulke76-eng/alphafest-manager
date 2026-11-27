"""HF56: recuperação e comparação de mensagens nos scripts reais do site.

O DOM funcional vem da fixture HF55; nenhum algoritmo do carrinho é simulado.
Storage, área de transferência e WhatsApp são locais, sem acessar serviços.
"""
from copy import deepcopy
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from site_quote_import_service import analisar_mensagem, preparar_rascunho
import test_site_cart_personalizations_hf55 as cart_dom


REVIEW_KEY = "alphafest_orcamento_mensagem_hf652456"


def item(line_id="ana", *, note="Nome: Ana", quantity=2):
    return {"id": "caneca-personalizada", "lineId": line_id, "name": "Caneca Personalizada",
            "quantity": quantity, "note": note, "image": ""}


def revision(items, text):
    signature = json.dumps([[row["lineId"], row["id"], row["name"], row["quantity"], row["note"]]
                            for row in items], ensure_ascii=False, separators=(",", ":"))
    return {"signature": signature, "text": text}


def saved_review(items, text, previous=()):
    return json.dumps({"version": 1, "current": revision(items, text),
                       "previous": [revision(items, old) for old in previous]}, ensure_ascii=False)


def change_and_generate(quantity):
    return [{"event": "back"}, {"event": "quantity", "value": quantity},
            {"event": "review"}, {"event": "regenerate"}]


class SiteCartMessageHF56Tests(unittest.TestCase):
    run_cart = cart_dom.SiteCartPersonalizationsHF55Tests.run_cart

    def test_back_review_and_reload_keep_exact_manual_text_without_rewriting_it(self):
        text = "  Meu nome é Maria.\nPreciso para 30/11. Retirada em Itatiba.\n  "
        states = self.run_cart([item()], [
            {"event": "review"}, {"event": "edit", "text": text}, {"event": "back"},
            {"event": "review"}, {"event": "close"}, {"event": "reload"},
            {"event": "show"}, {"event": "review"}, {"event": "copy"}, {"event": "send"},
        ])
        for index in range(2, len(states)):
            self.assertEqual(states[index]["message"], text)
            self.assertEqual(states[index]["reviewWrites"], 2)
            self.assertEqual(states[index]["reviewStorage"], states[2]["reviewStorage"])
        final = states[-1]
        self.assertEqual(final["copied"], [text])
        self.assertEqual(parse_qs(urlsplit(final["opened"][0]).query)["text"], [text.strip()])
        self.assertEqual(json.loads(final["reviewStorage"])["previous"], [])
        self.assertTrue(final["historyHidden"])
        self.assertEqual(final["items"], [item()])

    def test_valid_stored_revision_is_read_only_on_load_and_reopen(self):
        raw = saved_review([item()], "Mensagem já revisada pelo cliente")
        states = self.run_cart([item()], [{"event": "review"}, {"event": "back"},
            {"event": "review"}, {"event": "reload"}, {"event": "review"}], rawReviewStorage=raw)
        for state in states:
            self.assertEqual(state["reviewWrites"], 0)
            self.assertEqual(state["reviewStorage"], raw)
            self.assertEqual(state["message"], "Mensagem já revisada pelo cliente")
            self.assertFalse(state["readOnly"])
            self.assertTrue(state["warningHidden"])

    def test_intentionally_empty_message_survives_navigation_and_reload(self):
        for text in ("", "  \n "):
            with self.subTest(text=repr(text)):
                states = self.run_cart([item()], [{"event": "review"}, {"event": "edit", "text": text},
                    {"event": "back"}, {"event": "review"}, {"event": "reload"},
                    {"event": "review"}, {"event": "force-send"}, {"event": "copy"}])
                for state in states[2:]:
                    self.assertEqual(state["message"], text)
                    self.assertEqual(json.loads(state["reviewStorage"])["current"]["text"], text)
                    self.assertTrue(state["sendDisabled"])
                    self.assertEqual(state["reviewWrites"], 2)
                self.assertEqual(states[-1]["opened"], [])
                self.assertEqual(states[-1]["copied"], [])

    def test_every_item_change_blocks_stale_send_and_keeps_old_copy(self):
        items = [item("ana"), item("bia", note="Nome: Bia")]
        old = "Revisão manual com nome, data e retirada."
        variants = {
            "quantity": [{"event": "quantity", "value": 7}],
            "note": [{"event": "note", "value": "Nome: Carla"}],
            "new_row": [{"event": "another"}],
            "remove_row": [{"event": "remove", "row": 1}],
        }
        for field, value in (("name", "Caneca com outro nome"), ("id", "outro-produto"), ("lineId", "linha-nova")):
            changed = deepcopy(items)
            changed[0][field] = value
            variants[field] = [{"event": "storage-items", "items": changed}, {"event": "reload"}, {"event": "show"}]
        variants["order"] = [{"event": "storage-items", "items": list(reversed(items))}, {"event": "reload"}, {"event": "show"}]
        for name, actions in variants.items():
            with self.subTest(change=name):
                states = self.run_cart(items, [{"event": "show"}] + actions + [
                    {"event": "review"}, {"event": "force-send"}, {"event": "copy"}], rawReviewStorage=saved_review(items, old))
                final = states[-1]
                self.assertEqual(final["message"], old)
                self.assertTrue(final["readOnly"])
                self.assertTrue(final["sendDisabled"])
                self.assertFalse(final["warningHidden"])
                self.assertFalse(final["regenerateHidden"])
                self.assertIn("envio está desativado", final["reviewWarning"])
                self.assertEqual(final["reviewWrites"], 0)
                self.assertEqual(final["opened"], [])
                self.assertEqual(final["metrics"], [])
                self.assertEqual(final["copied"], [old])
                self.assertIn("Revisão anterior", final["copyStatus"])

    def test_row_order_and_multiplicity_matter_even_for_identical_products(self):
        items = [item("a"), item("b")]
        for changed in ([items[1], items[0]], [items[0]], items + [item("c")]):
            with self.subTest(lines=[row["lineId"] for row in changed]):
                final = self.run_cart(changed, [{"event": "review"}, {"event": "force-send"}],
                                      rawReviewStorage=saved_review(items, "Texto revisado"))[-1]
                self.assertTrue(final["sendDisabled"])
                self.assertTrue(final["readOnly"])
                self.assertEqual(final["opened"], [])

    def test_image_change_and_reverting_quantity_keep_compatible_review(self):
        original = item()
        changed = dict(original, image="https://example.invalid/nova.png")
        states = self.run_cart([changed], [{"event": "show"}, {"event": "quantity", "value": 3},
            {"event": "review"}, {"event": "back"}, {"event": "quantity", "value": 2},
            {"event": "review"}, {"event": "send"}], rawReviewStorage=saved_review([original], "Texto pessoal"))
        self.assertFalse(states[0]["sendDisabled"])
        self.assertTrue(states[3]["sendDisabled"])
        self.assertFalse(states[-1]["sendDisabled"])
        self.assertEqual(states[-1]["message"], "Texto pessoal")
        self.assertEqual(states[-1]["reviewWrites"], 0)
        self.assertEqual(len(states[-1]["opened"]), 1)

    def test_regenerate_preserves_previous_manual_text_and_restores_both_after_reload(self):
        old = "Meu nome é Maria. Preciso para 30/11. Retirada em Itatiba."
        states = self.run_cart([item()], [{"event": "show"}, {"event": "quantity", "value": 9},
            {"event": "review"}, {"event": "regenerate"}, {"event": "history-copy"},
            {"event": "reload"}, {"event": "review"}, {"event": "send"}], rawReviewStorage=saved_review([item()], old))
        updated = states[4]
        self.assertIn("Quantidade: 9", updated["message"])
        self.assertNotIn("Meu nome é Maria", updated["message"])
        self.assertFalse(updated["readOnly"])
        self.assertFalse(updated["sendDisabled"])
        self.assertTrue(updated["regenerateHidden"])
        self.assertEqual(updated["focused"], "afquote-message")
        self.assertEqual(updated["historyText"], old)
        self.assertFalse(updated["historyHidden"])
        self.assertEqual(states[5]["copied"], [old])
        self.assertEqual(states[-1]["message"], updated["message"])
        self.assertEqual(states[-1]["historyText"], old)
        self.assertEqual(states[-1]["reviewWrites"], 1)
        stored = json.loads(states[-1]["reviewStorage"])
        self.assertEqual(stored["previous"], [revision([item()], old)])
        self.assertEqual(len(states[-1]["metrics"]), 1)

    def test_automatic_regeneration_never_uses_manual_history_capacity(self):
        actions = [{"event": "review"}]
        for quantity in range(3, 18):
            actions += change_and_generate(quantity)
        final = self.run_cart([item()], actions)[-1]
        self.assertIn("Quantidade: 17", final["message"])
        self.assertEqual(json.loads(final["reviewStorage"])["previous"], [])
        self.assertTrue(final["historyHidden"])
        self.assertFalse(final["sendDisabled"])

    def test_manual_history_deduplicates_identical_text_and_keeps_empty_edit(self):
        actions = [{"event": "review"}, {"event": "edit", "text": "Retirada combinada"}]
        actions += change_and_generate(3)
        actions += [{"event": "edit", "text": "Retirada combinada"}] + change_and_generate(4)
        actions += [{"event": "edit", "text": ""}] + change_and_generate(5)
        actions += [{"event": "history-select", "index": 0}, {"event": "history-copy"}, {"event": "reload"}]
        final = self.run_cart([item()], actions)[-1]
        self.assertEqual([entry["text"] for entry in json.loads(final["reviewStorage"])["previous"]], ["Retirada combinada", ""])
        self.assertEqual(final["copied"], ["Retirada combinada"])
        self.assertEqual(final["historyText"], "")
        self.assertIn("texto vazio", final["historyOptions"][1]["text"])
        self.assertIn("Quantidade: 5", final["message"])

    def test_full_manual_history_does_not_block_unedited_automatic_message(self):
        generated = self.run_cart([item()], [{"event": "review"}])[-1]["message"]
        previous = [f"Ajuste pessoal {index}" for index in range(10)]
        states = self.run_cart([item()], [{"event": "show"}, {"event": "quantity", "value": 3},
            {"event": "review"}, {"event": "regenerate"}],
            rawReviewStorage=saved_review([item()], generated, previous))
        self.assertFalse(states[3]["regenerateDisabled"])
        self.assertIn("Quantidade: 3", states[-1]["message"])
        self.assertFalse(states[-1]["sendDisabled"])
        self.assertEqual([entry["text"] for entry in json.loads(states[-1]["reviewStorage"])["previous"]], previous)

    def test_full_history_requires_explicit_discard_and_does_not_erase_current(self):
        previous = [f"Ajuste pessoal {index}" for index in range(10)]
        current = "Meu último ajuste, ainda não arquivado"
        states = self.run_cart([item()], [{"event": "show"}, {"event": "quantity", "value": 3},
            {"event": "review"}, {"event": "force-regenerate"}, {"event": "copy"},
            {"event": "history-select", "index": 0}, {"event": "history-copy"},
            {"event": "history-discard"}, {"event": "regenerate"}],
            rawReviewStorage=saved_review([item()], current, previous))
        blocked = states[4]
        self.assertTrue(blocked["regenerateDisabled"])
        self.assertEqual(blocked["message"], current)
        self.assertEqual([entry["text"] for entry in json.loads(blocked["reviewStorage"])["previous"]], previous)
        self.assertIn("10 revisões", blocked["reviewWarning"])
        self.assertEqual(states[7]["copied"], [current, previous[0]])
        self.assertFalse(states[8]["regenerateDisabled"])
        self.assertEqual(states[8]["message"], current)
        final = states[-1]
        self.assertEqual([entry["text"] for entry in json.loads(final["reviewStorage"])["previous"]], previous[1:] + [current])
        self.assertEqual(final["items"], [dict(item(), quantity=3)])
        self.assertIn("Quantidade: 3", final["message"])
        self.assertEqual(len(final["confirms"]), 1)

    def test_cancelling_discard_and_clear_preserves_all_texts_and_items(self):
        raw = saved_review([item()], "Revisão atual", ["Revisão anterior"])
        final = self.run_cart([item()], [{"event": "review"}, {"event": "history-discard"},
            {"event": "back"}, {"event": "clear"}], rawReviewStorage=raw, confirm=False)[-1]
        self.assertEqual(final["reviewStorage"], raw)
        self.assertEqual(final["items"], [item()])
        self.assertEqual(final["message"], "Revisão atual")
        self.assertEqual(final["historyText"], "Revisão anterior")
        self.assertEqual(final["reviewWrites"], 0)
        self.assertEqual(len(final["confirms"]), 2)

    def test_removing_last_item_still_allows_copy_and_explicit_clear_of_reviews(self):
        states = self.run_cart([item()], [{"event": "show"}, {"event": "remove"},
            {"event": "review"}, {"event": "force-send"}, {"event": "copy"},
            {"event": "back"}, {"event": "clear"}, {"event": "reload"}, {"event": "show"}],
            rawReviewStorage=saved_review([item()], "Texto recuperável", ["Anterior guardada"]))
        empty = states[2]
        self.assertEqual(empty["items"], [])
        self.assertFalse(empty["reviewDisabled"])
        self.assertFalse(empty["clearDisabled"])
        self.assertTrue(empty["sendDisabled"])
        self.assertTrue(empty["regenerateDisabled"])
        self.assertEqual(states[5]["copied"], ["Texto recuperável"])
        final = states[-1]
        self.assertEqual(final["items"], [])
        self.assertEqual(json.loads(final["reviewStorage"]), {"version": 1, "current": None, "previous": []})
        self.assertEqual(final["message"], "")
        self.assertEqual(final["historyText"], "")
        self.assertTrue(final["historyHidden"])
        self.assertTrue(final["reviewDisabled"])
        self.assertTrue(final["clearDisabled"])
        self.assertEqual(final["opened"], [])

    def test_long_prior_revision_has_integral_clipboard_and_selection_fallbacks(self):
        items = [item(f"linha-{index}", note=(f"Nome {index}: " + "x" * 450)[:450]) for index in range(25)]
        old = "  Anotações pessoais\n" + "🎈 observações longas; " * 1000 + "\nFIM  "
        for clipboard in ("success", "fallback", "manual"):
            with self.subTest(clipboard=clipboard):
                states = self.run_cart(items, [{"event": "show"}, {"event": "quantity", "value": 4},
                    {"event": "review"}, {"event": "regenerate"}, {"event": "history-copy"},
                    {"event": "copy"}, {"event": "send"}], rawReviewStorage=saved_review(items, old), clipboard=clipboard)
                final = states[-1]
                self.assertEqual(final["historyText"], old)
                self.assertIn("Nome 24:", final["message"])
                self.assertFalse(final["helpHidden"])
                self.assertEqual(final["opened"], ["https://wa.me/5511999991234"])
                self.assertEqual(len(final["metrics"]), 1)
                if clipboard == "manual":
                    self.assertEqual(final["copied"], [])
                    self.assertTrue(final["historySelected"])
                    self.assertTrue(final["selected"])
                    self.assertIn("opção Copiar", final["historyStatus"])
                else:
                    self.assertEqual(final["copied"], [old, final["message"]])

    def test_failed_storage_write_keeps_session_review_and_explains_recovery_limit(self):
        for failure in (True, REVIEW_KEY):
            with self.subTest(failure=failure):
                actions = [{"event": "review"}, {"event": "edit", "text": "Texto que não pode sumir"},
                           {"event": "back"}, {"event": "review"}]
                actions += change_and_generate(6) + [{"event": "history-copy"}, {"event": "send"}]
                states = self.run_cart([item()], actions, failStorageWrite=failure)
                self.assertEqual(states[4]["message"], "Texto que não pode sumir")
                final = states[-1]
                self.assertEqual(final["historyText"], "Texto que não pode sumir")
                self.assertEqual(final["copied"], ["Texto que não pode sumir"])
                self.assertIn("Quantidade: 6", final["message"])
                self.assertEqual(final["reviewStorage"], None)
                self.assertFalse(final["storageNoteHidden"])
                self.assertIn("continuar nesta aba", final["storageNote"])
                self.assertIn("antes de fechar ou recarregar", final["storageNote"])
                self.assertEqual(len(final["opened"]), 1)

    def test_storage_read_denied_does_not_prevent_new_order_and_manual_review(self):
        final = self.run_cart([], [{"event": "open", "product": "caneca-personalizada"},
            {"event": "add"}, {"event": "review"}, {"event": "edit", "text": "Pedido nesta aba"},
            {"event": "back"}, {"event": "review"}, {"event": "copy"}, {"event": "send"}],
            failStorageRead=True, failStorageWrite=True)[-1]
        self.assertEqual(final["message"], "Pedido nesta aba")
        self.assertEqual(final["copied"], ["Pedido nesta aba"])
        self.assertFalse(final["storageNoteHidden"])
        self.assertEqual(len(final["opened"]), 1)

    def test_invalid_review_json_keys_types_and_limits_do_not_replace_items(self):
        valid = json.loads(saved_review([item()], "Texto revisado"))
        bad_signature = json.loads(valid["current"]["signature"])
        bad_signature[0][3] = "2"
        cases = ["{quebrado", "null", "[]", json.dumps(dict(valid, constructor={})),
                 json.dumps(dict(valid, __proto__={})), json.dumps(dict(valid, version=2)),
                 json.dumps(dict(valid, current={"signature": valid["current"]["signature"], "text": 1})),
                 json.dumps(dict(valid, current={"signature": json.dumps(bad_signature), "text": "X"})),
                 json.dumps(dict(valid, current={"signature": "null", "text": "X"})),
                 json.dumps(dict(valid, current={"signature": valid["current"]["signature"], "text": "x" * 100001})),
                 json.dumps(dict(valid, previous=[revision([item()], "Duplicada")] * 2)),
                 json.dumps(dict(valid, previous=[revision([item()], str(index)) for index in range(11)])),
                 json.dumps(dict(valid, current=None, previous=[revision([item()], "Revisão sem atual")])),
                 " " * 2000001]
        for index, raw in enumerate(cases):
            with self.subTest(case=index):
                states = self.run_cart([item()], [{"event": "review"}], rawReviewStorage=raw)
                self.assertEqual(states[0]["reviewStorage"], raw)
                self.assertEqual(states[0]["reviewWrites"], 0)
                self.assertEqual(states[0]["message"], "")
                self.assertIn("formato é inválido", states[0]["storageNote"])
                self.assertEqual(states[0]["items"], [item()])
                self.assertIn("1. Caneca Personalizada", states[1]["message"])
                self.assertEqual(json.loads(states[1]["reviewStorage"])["previous"], [])
                self.assertTrue(states[1]["storageNoteHidden"])

    def test_text_above_recovery_limit_is_not_truncated_or_claimed_saved(self):
        text = "x" * 100001
        states = self.run_cart([item()], [{"event": "review"}, {"event": "edit", "text": text},
            {"event": "back"}, {"event": "review"}, {"event": "copy"}])
        self.assertEqual(states[-1]["message"], text)
        self.assertEqual(states[-1]["copied"], [text])
        self.assertEqual(states[-1]["reviewStorage"], states[1]["reviewStorage"])
        self.assertFalse(states[-1]["storageNoteHidden"])

    def test_untrusted_message_and_item_text_stay_literal_in_current_and_history(self):
        malicious = '</textarea><img id="injected" src=x onerror="alert(1)"> & "fim"'
        source = item(note=malicious)
        states = self.run_cart([source], [{"event": "show"}, {"event": "quantity", "value": 4},
            {"event": "review"}, {"event": "regenerate"}, {"event": "history-copy"}, {"event": "reload"}],
            rawReviewStorage=saved_review([source], malicious))
        self.assertTrue(all(not state["injected"] for state in states))
        self.assertEqual(states[-1]["historyText"], malicious)
        self.assertIn(malicious, states[-1]["message"])
        self.assertEqual(states[-1]["copied"], [malicious])
        self.assertIn("&lt;/textarea&gt;", states[1]["html"])

    def test_focus_moves_to_required_action_then_current_message_and_back(self):
        states = self.run_cart([item()], [{"event": "show"}, {"event": "quantity", "value": 4},
            {"event": "review"}, {"event": "regenerate"}, {"event": "history-discard"},
            {"event": "back"}, {"event": "review"}, {"event": "key", "key": "Escape"}],
            rawReviewStorage=saved_review([item()], "Texto manual"), mobile=True)
        self.assertEqual(states[3]["focused"], "afquote-regenerate")
        self.assertEqual(states[4]["focused"], "afquote-message")
        self.assertEqual(states[5]["focused"], "afquote-message")
        self.assertEqual(states[6]["focused"], "afquote-review")
        self.assertEqual(states[7]["focused"], "afquote-message")
        self.assertTrue(states[8]["hidden"])

    def test_regenerated_message_reaches_hf54_with_each_personalization_intact(self):
        items = [item("ana", note="Nome: Ana\nCor: azul"), item("bia", note="Nome: Bia\nCor: rosa", quantity=3)]
        final = self.run_cart(items, [{"event": "show"}, {"event": "quantity", "value": 4},
            {"event": "review"}, {"event": "regenerate"}, {"event": "copy"}],
            rawReviewStorage=saved_review(items, "Meu texto adicional deve continuar disponível"))[-1]
        parsed = analisar_mensagem(final["copied"][0], cart_dom.CATALOG)
        self.assertEqual(parsed["erros"], [])
        self.assertEqual(len(parsed["itens"]), 2)
        self.assertEqual([row["quantidade"] for row in parsed["itens"]], [4, 3])
        self.assertEqual([row["especificacoes"] for row in parsed["itens"]], [row["note"] for row in items])
        draft = preparar_rascunho(parsed, deepcopy(parsed["itens"]))
        self.assertEqual(len(draft["itens"]), 2)
        self.assertEqual([row["quantidade"] for row in draft["itens"]], [4, 3])
        self.assertEqual([row["produto_catalogo_id"] for row in draft["itens"]], ["CAT-01", "CAT-01"])
        self.assertEqual([row["especificacoes"] for row in draft["itens"]], [row["note"] for row in items])
        self.assertEqual(final["historyText"], "Meu texto adicional deve continuar disponível")


if __name__ == "__main__":
    unittest.main()
