"""Unit tests for MessageExtractor CSV export helpers and columns."""

import csv
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from messages import CSV_COLUMNS, MessageExtractor  # noqa: E402


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

    def test_csv_attachments_empty(self):
        self.assertEqual(self.ext._csv_attachments({"attachments": []}), "")

    def test_csv_attachments_json(self):
        raw = self.ext._csv_attachments({
            "attachments": [{
                "transfer_name": "photo.jpg",
                "filename": "~/Library/SMS/Attachments/x/photo.jpg",
                "mime_type": "image/jpeg",
                "total_bytes": 1234,
            }],
        })
        parsed = json.loads(raw)
        self.assertEqual(parsed[0]["filename"], "photo.jpg")
        self.assertEqual(parsed[0]["mime_type"], "image/jpeg")
        self.assertEqual(parsed[0]["total_bytes"], 1234)

    def test_csv_row_column_count(self):
        row = self.ext._csv_row(_sample_msg())
        self.assertEqual(len(row), len(CSV_COLUMNS))
        self.assertEqual(row[CSV_COLUMNS.index("Direction")], "Sent")
        self.assertEqual(row[CSV_COLUMNS.index("Message ID")], 42)
        self.assertEqual(row[CSV_COLUMNS.index("Text")], "hello")


class TestCsvExport(unittest.TestCase):
    def setUp(self):
        self.ext = MessageExtractor.__new__(MessageExtractor)
        self.ext._inner = MagicMock()

    def test_export_csv_header_and_row(self):
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
                    "transfer_name": "clip.mp4",
                    "mime_type": "video/mp4",
                    "total_bytes": 99,
                }],
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = self.ext._export_csv(messages, chat_id=1654, output_dir=tmp)
            path = result["file"]
            self.assertTrue(os.path.exists(path))
            with open(path, newline="", encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], CSV_COLUMNS)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[1][CSV_COLUMNS.index("Chat Identifier")], "+15559876543")
            self.assertEqual(rows[2][CSV_COLUMNS.index("Direction")], "Received")
            atts = json.loads(rows[2][CSV_COLUMNS.index("Attachments")])
            self.assertEqual(atts[0]["filename"], "clip.mp4")

    def test_export_merged_csv_uses_same_columns(self):
        messages = [_sample_msg(_conversation="A"), _sample_msg(_conversation="B", message_id=7)]
        with tempfile.TemporaryDirectory() as tmp:
            result = self.ext._export_merged_csv(messages, output_dir=tmp)
            path = result["files"][0]
            with open(path, newline="", encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], CSV_COLUMNS)
            self.assertEqual(rows[1][CSV_COLUMNS.index("Conversation")], "A")
            self.assertEqual(rows[2][CSV_COLUMNS.index("Conversation")], "B")


if __name__ == "__main__":
    unittest.main()
