import logging
import unittest

from os import getenv as osgetenv
from sys import path as syspath
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)

syspath.insert(1, str(Path("..", "..", "catdv_resolve", "src").resolve()))

from catdv_resolve import resolve as resolve_api_mappings

syspath.insert(1, str(Path("..", "src").resolve()))

from catdv_resolve_tests.generic import *
from catdv_resolve_tests.utility import Helper

syspath.append(str(Path(osgetenv("RESOLVE_SCRIPT_API"), "Modules")))


def setUpModule():
    UnsafeResolveAppTest.Resolve = ResolveScriptAppContainer()
    UnsafeResolveAppTest.Resolve.set_up()


def tearDownModule():
    UnsafeResolveAppTest.Resolve.clean_up()


class TestAPIAccess(UnsafeResolveAppTest):
    def test_api_script_can_be_found(self):
        self.assertIsNotNone(self.Resolve.Script)

    def test_api_script_provides_resolve_object(self):
        self.assertIsNotNone(self.Resolve.App)


class TestMediaImport(TestWithOneClip):
    def test_still_image_import(self):
        self.import_clip(Path(self.Assets, "image", "vacationcapy.png"))
        self.assertEqual("Still", self.clip.get_clip_property("Type"))

    def test_audio_import(self):
        self.import_clip(Path(self.Assets, "audio", "Not Too Late.mp3"))
        self.assertEqual("Audio", self.clip.get_clip_property("Type"))

    def test_movie_import(self):
        self.import_clip(Path(self.Assets, "movie", "Flawless mishap.mp4"))
        self.assertEqual("Video + Audio", self.clip.get_clip_property("Type"))

    @unittest.skip(reason="No video-only test content, yet.")
    def test_video_only_import(self):
        self.import_clip(Path(self.Assets, "video", "blah"))
        self.assertEqual("Video", self.clip.get_clip_property("Type"))


class TestClipMetadata(TestWithOneClip):
    def setUp(self) -> None:
        super(TestClipMetadata, self).setUp()
        self.import_clip(Path(self.Assets, "movie", "scuffed jumping.mp4"))

    def test_set_name(self):
        string = Helper.random.ascii_string(10)
        self.clip.set_name(string)
        self.assertEqual(string, self.clip.get_name())

    def test_set_comment(self):
        string = Helper.random.ascii_string(10)
        self.clip.set_comment(string)
        self.assertEqual(string, self.clip.get_metadata("Comments"))

    def test_set_description(self):
        string = Helper.random.ascii_string(10)
        self.clip.set_description(string)
        self.assertEqual(string, self.clip.get_metadata("Description"))

    def test_set_keywords(self):
        strings = tuple([Helper.random.ascii_string(5) for _ in range(3)])
        self.clip.set_keywords(strings)
        self.assertEqual(",".join(strings), self.clip.get_metadata("Keywords"))

    def test_add_frame_marker(self):
        marker_to_add = resolve_api_mappings.Marker(
            "Test Frame Marker",
            "Comment blah blah",
            5,
            1,
            "Red",
            "TestFrameMarker"
        )
        self.clip.add_marker(marker_to_add)
        marker_added = self.clip.get_marker_by_custom_data(marker_to_add.custom_data)
        self.assertEqual(marker_to_add, marker_added)

    def test_add_duration_marker(self):
        marker_to_add = resolve_api_mappings.Marker(
            "Test Duration Marker",
            "Comment blah blah",
            5,
            10,
            "Red",
            "TestDurationMarker"
        )
        self.clip.add_marker(marker_to_add)
        marker_added = self.clip.get_marker_by_custom_data(marker_to_add.custom_data)
        self.assertEqual(marker_to_add, marker_added)


if __name__ == "__main__":
    unittest.main()
