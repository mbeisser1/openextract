"""Tests for messages.py — MessageExtractor helpers."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, "python")

from messages import MessageExtractor


class TestResolveMimeType(unittest.TestCase):
    def setUp(self):
        self.ex = MessageExtractor()

    def test_uses_db_mime_lowercased(self):
        self.assertEqual(
            self.ex._resolve_mime_type("Image/JPEG", "public.png", ""),
            "image/jpeg",
        )

    def test_maps_uti_when_mime_missing(self):
        self.assertEqual(
            self.ex._resolve_mime_type(None, "com.apple.m4a-audio", ""),
            "audio/mp4",
        )
        self.assertEqual(
            self.ex._resolve_mime_type("", "public.heic", ""),
            "image/heic",
        )

    def test_magic_bytes(self):
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(bytes.fromhex("ffd8ffe000104a464946"))  # JPEG SOI
            path = f.name
        try:
            self.assertEqual(
                self.ex._resolve_mime_type(None, None, path),
                "image/jpeg",
            )
        finally:
            os.unlink(path)

    def test_extension_fallback_when_magic_finds_nothing(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"not-identifiable-bytes")
            path = f.name
        try:
            with patch("messages.puremagic.magic_file", return_value=[]):
                self.assertEqual(
                    self.ex._resolve_mime_type(None, None, path),
                    "image/png",
                )
        finally:
            os.unlink(path)

    def test_when_nothing_matches(self):
        self.assertEqual(
            self.ex._resolve_mime_type(None, "com.example.unknown", ""),
            "application/octet-stream",
        )


if __name__ == "__main__":
    unittest.main()
