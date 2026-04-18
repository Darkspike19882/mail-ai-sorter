import unittest

from services import inbox_service


class InboxServiceContractTests(unittest.TestCase):
    def test_normalize_mail_item_maps_search_shape_to_inbox_shape(self):
        normalized = inbox_service.normalize_mail_item(
            {
                "msg_uid": 42,
                "account": "Personal",
                "folder": "INBOX",
                "from_addr": "Ada <ada@example.com>",
                "subject": "Status",
                "date_iso": "2026-04-17T10:30:00+00:00",
            }
        )

        self.assertEqual(normalized["uid"], "42")
        self.assertEqual(normalized["msg_uid"], "42")
        self.assertEqual(normalized["from"], "Ada <ada@example.com>")
        self.assertEqual(normalized["from_addr"], "Ada <ada@example.com>")
        self.assertEqual(normalized["date"], "2026-04-17T10:30:00+00:00")
        self.assertEqual(normalized["date_iso"], "2026-04-17T10:30:00+00:00")
        self.assertTrue(normalized["seen"])
        self.assertFalse(normalized["flagged"])

    def test_merge_unified_inbox_results_surfaces_failures_and_keeps_order(self):
        merged = inbox_service.merge_unified_inbox_results(
            [
                {
                    "account": "Alpha",
                    "emails": [
                        {
                            "uid": "1",
                            "account": "Alpha",
                            "folder": "INBOX",
                            "from": "alpha@example.com",
                            "subject": "Older",
                            "date": "Thu, 17 Apr 2026 08:00:00 +0000",
                        }
                    ],
                    "total": 1,
                    "error": None,
                },
                {
                    "account": "Broken",
                    "emails": [],
                    "total": 0,
                    "error": "IMAP timeout",
                },
                {
                    "account": "Beta",
                    "emails": [
                        {
                            "uid": "2",
                            "account": "Beta",
                            "folder": "INBOX",
                            "from": "beta@example.com",
                            "subject": "Newer",
                            "date": "Thu, 17 Apr 2026 09:00:00 +0000",
                        }
                    ],
                    "total": 1,
                    "error": None,
                },
            ],
            page=1,
            per_page=10,
        )

        self.assertTrue(merged["degraded"])
        self.assertEqual(merged["total"], 2)
        self.assertEqual(
            merged["failures"], [{"account": "Broken", "error": "IMAP timeout"}]
        )
        self.assertEqual(
            [mail["account"] for mail in merged["emails"]], ["Beta", "Alpha"]
        )


if __name__ == "__main__":
    unittest.main()
