"""Tests for CSV/HTML attachment export (companion CSV + binary copy)."""

import csv
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from messages import ATTACHMENT_CSV_COLUMNS, MessageExtractor  # noqa: E402


def _sample_msg(**overrides):
    base = {
        "message_id": 42,
        "text": "hello",
        "message_type": "text",
        "date": "2025-12-18T16:32:15+00:00",
        "is_from_me": True,
        "sender": "me",
        "has_attachments": False,
        "attachments": [],
    }
    base.update(overrides)
    return base


class TestCsvAttachmentExport(unittest.TestCase):
    def setUp(self):
        self.ext = MessageExtractor.__new__(MessageExtractor)
        self.ext._inner = MagicMock()

    def test_export_csv_keeps_original_columns_and_writes_companion(self):
        messages = [
            _sample_msg(),
            _sample_msg(
                message_id=43,
                is_from_me=False,
                sender="Kevin",
                text="",
                has_attachments=True,
                attachments=[{
                    "attachment_id": 9,
                    "transfer_name": "clip.mp4",
                    "mime_type": "video/mp4",
                }],
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "src.bin")
            with open(src, "wb") as f:
                f.write(b"video-bytes")
            self.ext._resolve_attachment_path = MagicMock(return_value={
                "path": src,
                "filename": "clip.mp4",
                "mime_type": "video/mp4",
            })
            out = os.path.join(tmp, "out")
            os.makedirs(out)
            result = self.ext._export_csv(messages, chat_id=1654, output_dir=out, backup=object())

            with open(result["file"], newline="", encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))
            self.assertEqual(
                rows[0],
                ["Date", "Sender", "Text", "Is From Me", "Has Attachments"],
            )
            self.assertEqual(result["attachments_exported"], 1)
            dest = os.path.join(out, "attachments", "43_9_clip.mp4")
            self.assertTrue(os.path.exists(dest))

            with open(result["attachments_file"], newline="", encoding="utf-8-sig") as f:
                att_rows = list(csv.reader(f))
            self.assertEqual(att_rows[0], ATTACHMENT_CSV_COLUMNS)
            path_col = ATTACHMENT_CSV_COLUMNS.index("Exported Path")
            self.assertEqual(att_rows[1][path_col], "attachments/43_9_clip.mp4")

    def test_export_csv_missing_attachment_leaves_path_empty(self):
        self.ext._resolve_attachment_path = MagicMock(
            return_value={"error": "Attachment file not found in backup"}
        )
        messages = [
            _sample_msg(
                message_id=43,
                has_attachments=True,
                attachments=[{
                    "attachment_id": 9,
                    "transfer_name": "missing.mp4",
                    "mime_type": "video/mp4",
                }],
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = self.ext._export_csv(messages, chat_id=1, output_dir=tmp, backup=object())
            self.assertEqual(result["attachments_exported"], 0)
            self.assertEqual(result["attachments_failed"], 1)
            with open(result["attachments_file"], newline="", encoding="utf-8-sig") as f:
                att_rows = list(csv.reader(f))
            path_col = ATTACHMENT_CSV_COLUMNS.index("Exported Path")
            self.assertEqual(att_rows[1][path_col], "")


class TestHtmlAttachmentExport(unittest.TestCase):
    def setUp(self):
        self.ext = MessageExtractor.__new__(MessageExtractor)
        self.ext._inner = MagicMock()

    def test_export_html_embeds_image_and_links_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            img_src = os.path.join(tmp, "photo.jpg")
            file_src = os.path.join(tmp, "doc.pdf")
            with open(img_src, "wb") as f:
                f.write(b"jpeg")
            with open(file_src, "wb") as f:
                f.write(b"%PDF")

            def resolve(_backup, att_id):
                if att_id == 1:
                    return {"path": img_src, "filename": "photo.jpg", "mime_type": "image/jpeg"}
                if att_id == 2:
                    return {"path": file_src, "filename": "doc.pdf", "mime_type": "application/pdf"}
                return {"error": "missing"}

            self.ext._resolve_attachment_path = MagicMock(side_effect=resolve)
            messages = [
                _sample_msg(
                    message_id=10,
                    text="see this",
                    has_attachments=True,
                    attachments=[{
                        "attachment_id": 1,
                        "transfer_name": "photo.jpg",
                        "mime_type": "image/jpeg",
                    }],
                ),
                _sample_msg(
                    message_id=11,
                    text="",
                    is_from_me=False,
                    sender="Kevin",
                    has_attachments=True,
                    attachments=[{
                        "attachment_id": 2,
                        "transfer_name": "doc.pdf",
                        "mime_type": "application/pdf",
                    }],
                ),
            ]
            out = os.path.join(tmp, "out")
            os.makedirs(out)
            result = self.ext._export_html(messages, chat_id=7, output_dir=out, backup=object())
            with open(result["file"], encoding="utf-8") as f:
                content = f.read()
            self.assertIn('src="attachments/10_1_photo.jpg"', content)
            self.assertIn('href="attachments/11_2_doc.pdf"', content)
            self.assertIn("doc.pdf", content)
            self.assertEqual(result["attachments_exported"], 2)


if __name__ == "__main__":
    unittest.main()
