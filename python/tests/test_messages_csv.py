"""Unit tests for MessageExtractor CSV export helpers and columns."""

import csv
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from messages import ATTACHMENT_CSV_COLUMNS, CSV_COLUMNS, MessageExtractor  # noqa: E402


def _sample_msg(**overrides):
    base = {
        "message_id": 42,
        "text": "hello",
        "message_type": "text",
        "link_preview": None,
        "date": "2025-12-18T16:32:15+00:00",
        "is_from_me": True,
        "sender": "me",
        "sender_handle": "+15551234567",
        "has_attachments": False,
        "attachments": [],
        "is_reaction": False,
        "_chat_identifier": "+15559876543",
        "_conversation": "Kevin",
        "_service": "iMessage",
        "_conversation_type": "individual",
    }
    base.update(overrides)
    return base


class TestCsvHelpers(unittest.TestCase):
    def setUp(self):
        self.ext = MessageExtractor.__new__(MessageExtractor)

    def test_csv_direction(self):
        self.assertEqual(self.ext._csv_direction({"is_from_me": True}), "Sent")
        self.assertEqual(self.ext._csv_direction({"is_from_me": False}), "Received")

    def test_csv_link_url(self):
        self.assertEqual(self.ext._csv_link_url({}), "")
        self.assertEqual(
            self.ext._csv_link_url({"link_preview": {"url": "https://example.com"}}),
            "https://example.com",
        )

    def test_csv_row_has_no_attachments_column(self):
        self.assertNotIn("Attachments", CSV_COLUMNS)
        row = self.ext._csv_row(_sample_msg())
        self.assertEqual(len(row), len(CSV_COLUMNS))
        self.assertEqual(row[CSV_COLUMNS.index("Direction")], "Sent")
        self.assertEqual(row[CSV_COLUMNS.index("Message ID")], 42)
        self.assertEqual(row[CSV_COLUMNS.index("Text")], "hello")

    def test_attachment_csv_rows_multi(self):
        msg = _sample_msg(
            message_id=1004,
            has_attachments=True,
            attachments=[
                {
                    "attachment_id": 8812,
                    "transfer_name": "IMG_1234.HEIC",
                    "mime_type": "image/heic",
                },
                {
                    "attachment_id": 8813,
                    "filename": "~/Library/SMS/Attachments/x/clip.MOV",
                    "mime_type": "video/quicktime",
                },
            ],
        )
        rows = self.ext._attachment_csv_rows([msg])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][ATTACHMENT_CSV_COLUMNS.index("Filename")], "IMG_1234.HEIC")
        self.assertEqual(rows[1][ATTACHMENT_CSV_COLUMNS.index("Filename")], "clip.MOV")
        self.assertEqual(rows[1][ATTACHMENT_CSV_COLUMNS.index("Attachment ID")], 8813)


class TestCsvExport(unittest.TestCase):
    def setUp(self):
        self.ext = MessageExtractor.__new__(MessageExtractor)
        self.ext._inner = MagicMock()

    def test_export_csv_writes_companion_attachments(self):
        messages = [
            _sample_msg(),
            _sample_msg(
                message_id=43,
                is_from_me=False,
                sender="Kevin",
                text="",
                message_type="attachment",
                has_attachments=True,
                attachments=[{
                    "attachment_id": 9,
                    "transfer_name": "clip.mp4",
                    "mime_type": "video/mp4",
                }],
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = self.ext._export_csv(messages, chat_id=1654, output_dir=tmp)
            path = result["file"]
            att_path = result["attachments_file"]
            self.assertTrue(os.path.exists(path))
            self.assertTrue(os.path.exists(att_path))
            self.assertEqual(result["attachment_count"], 1)
            with open(path, newline="", encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], CSV_COLUMNS)
            self.assertNotIn("Attachments", rows[0])
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[2][CSV_COLUMNS.index("Has Attachments")], "True")
            with open(att_path, newline="", encoding="utf-8-sig") as f:
                att_rows = list(csv.reader(f))
            self.assertEqual(att_rows[0], ATTACHMENT_CSV_COLUMNS)
            self.assertEqual(len(att_rows), 2)
            self.assertEqual(att_rows[1][ATTACHMENT_CSV_COLUMNS.index("Filename")], "clip.mp4")
            self.assertEqual(att_rows[1][ATTACHMENT_CSV_COLUMNS.index("Message ID")], "43")

    def test_export_csv_writes_empty_attachments_file(self):
        messages = [_sample_msg()]
        with tempfile.TemporaryDirectory() as tmp:
            result = self.ext._export_csv(messages, chat_id=1, output_dir=tmp)
            att_path = result["attachments_file"]
            self.assertEqual(result["attachment_count"], 0)
            with open(att_path, newline="", encoding="utf-8-sig") as f:
                att_rows = list(csv.reader(f))
            self.assertEqual(att_rows, [ATTACHMENT_CSV_COLUMNS])

    def test_export_merged_csv_uses_same_columns(self):
        messages = [_sample_msg(_conversation="A"), _sample_msg(_conversation="B", message_id=7)]
        with tempfile.TemporaryDirectory() as tmp:
            result = self.ext._export_merged_csv(messages, output_dir=tmp)
            self.assertEqual(len(result["files"]), 2)
            path = result["files"][0]
            att_path = result["files"][1]
            with open(path, newline="", encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], CSV_COLUMNS)
            self.assertEqual(rows[1][CSV_COLUMNS.index("Conversation")], "A")
            self.assertEqual(rows[2][CSV_COLUMNS.index("Conversation")], "B")
            self.assertTrue(att_path.endswith("all_conversations_attachments.csv"))
            with open(att_path, newline="", encoding="utf-8-sig") as f:
                att_rows = list(csv.reader(f))
            self.assertEqual(att_rows[0], ATTACHMENT_CSV_COLUMNS)


if __name__ == "__main__":
    unittest.main()
