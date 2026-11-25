"""Regressões do funil por sessão; todas as linhas são fixtures em memória."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

import site_metrics_service as metrics


class TestProductWhatsAppFunnel(unittest.TestCase):
    def setUp(self):
        self.end = datetime(2026, 11, 25, 15, tzinfo=timezone.utc)
        self.start = self.end - timedelta(days=30)

    @staticmethod
    def row(session, timestamp, event="product_open"):
        return {"session_id": session, "created_at": timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
                "event_type": event, "page_path": "/", "product_name": "Caneca"}

    def converted(self, products, contacts):
        return metrics._product_to_whatsapp_sessions(products, contacts, self.start, self.end)

    def test_only_same_session_in_strict_order_converts(self):
        opened = self.end - timedelta(minutes=10)
        products = [self.row("a", opened), self.row("b", opened), self.row("c", opened)]
        contacts = [self.row("a", opened + timedelta(seconds=1)),
                    self.row("b", opened - timedelta(seconds=1)),
                    self.row("direct", opened + timedelta(seconds=1))]
        self.assertEqual(self.converted(products, contacts), {"a"})

    def test_equal_timestamps_do_not_establish_order(self):
        at = self.end - timedelta(minutes=10)
        self.assertEqual(self.converted([self.row("a", at)], [self.row("a", at)]), set())

    def test_duplicates_and_out_of_order_input_count_session_once(self):
        at = self.end - timedelta(minutes=10)
        products = [self.row("a", at + timedelta(minutes=2)), self.row("a", at), self.row("a", at)]
        contacts = [self.row("a", at + timedelta(minutes=1))] * 3
        original = copy.deepcopy((products, contacts))
        self.assertEqual(self.converted(products, contacts), {"a"})
        self.assertEqual((products, contacts), original)

    def test_both_events_must_be_in_inclusive_window(self):
        products = [self.row("lower", self.start), self.row("upper", self.end - timedelta(seconds=1)),
                    self.row("old", self.start - timedelta(microseconds=1)),
                    self.row("future", self.end - timedelta(seconds=1))]
        contacts = [self.row("lower", self.start + timedelta(seconds=1)), self.row("upper", self.end),
                    self.row("old", self.start + timedelta(seconds=1)),
                    self.row("future", self.end + timedelta(microseconds=1))]
        self.assertEqual(self.converted(products, contacts), {"lower", "upper"})

    def test_missing_invalid_timestamps_or_sessions_do_not_convert(self):
        products = [self.row("", self.start), self.row("   ", self.start), self.row("bad", "n/a"),
                    self.row("missing", None), self.row("overflow", "9999-12-31T23:59:59-03:00"),
                    self.row("invalid_contact", self.start)]
        contacts = [self.row("", self.end), self.row("   ", self.end), self.row("bad", self.end),
                    self.row("missing", self.end), self.row("invalid_contact", "invalid")]
        self.assertEqual(self.converted(products, contacts), set())
        self.assertEqual(metrics._session_ids(products, self.start, self.end), {"invalid_contact"})

    def test_naive_utc_and_timezone_offsets_compare_as_instants(self):
        products = [self.row("a", "2026-11-25T12:00:00"), self.row("equal", "2026-11-25T12:00:00Z")]
        contacts = [self.row("a", "2026-11-25T09:00:01-03:00"),
                    self.row("equal", "2026-11-25T09:00:00-03:00")]
        self.assertEqual(self.converted(products, contacts), {"a"})

    def test_dashboard_preserves_direct_contacts_without_inflating_product_conversion(self):
        at = self.end - timedelta(minutes=10)
        rows = [self.row(sid, at - timedelta(minutes=1), "page_view") for sid in ("a", "b", "direct1", "direct2")]
        rows += [self.row("a", at), self.row("b", at)]
        rows += [self.row(sid, at + timedelta(seconds=1), "whatsapp_click") for sid in ("a", "a", "direct1", "direct2")]
        with patch.object(metrics, "_dashboard_rows", return_value=rows):
            summary = metrics.dashboard_summary(self.end)
        for key in ("today", "7d", "30d"):
            period = summary["periods"][key]
            self.assertEqual(period["product_sessions"], 2)
            self.assertEqual(period["whatsapp"], 4)
            self.assertEqual(period["whatsapp_sessions"], 3)
            self.assertEqual(period["product_to_whatsapp_sessions"], 1)
            self.assertEqual(period["whatsapp_other_sessions"], 2)
            self.assertEqual(period["conv_product_to_whatsapp"], 50.0)

    def test_empty_product_denominator_is_zero_and_direct_contact_remains(self):
        rows = [self.row("direct", self.end - timedelta(seconds=1), "whatsapp_click")]
        with patch.object(metrics, "_dashboard_rows", return_value=rows):
            period = metrics.dashboard_summary(self.end)["periods"]["30d"]
        self.assertEqual(period["conv_product_to_whatsapp"], 0.0)
        self.assertEqual(period["whatsapp_sessions"], 1)
        self.assertEqual(period["whatsapp_other_sessions"], 1)


if __name__ == "__main__":
    unittest.main()
