from typing import Optional
import logging
import unittest
from pathlib import Path
from sys import exit as sysexit

from catdv_resolve import exceptions
from catdv_resolve import resolve as resolve_api_mappings


class ResolveScriptAppContainer:
    __slots__ = ["Script", "App", "WrappedApp"]

    def __init__(self):
        try:
            import DaVinciResolveScript as resolve_script
            resolve_app = resolve_script.scriptapp("Resolve")
        except ImportError:
            resolve_script = None
            resolve_app = None

        try:
            assert resolve_app is not None
            wrapped_app = resolve_api_mappings.ResolveHandler(resolve_app)
        except AssertionError:
            wrapped_app = None

        self.Script = resolve_script
        self.App = resolve_app
        self.WrappedApp = wrapped_app

    def set_up(self):
        if self.WrappedApp is None:
            return

        logging.info("Beginning Resolve setup...")

        self.clean_up()

        self.WrappedApp.get_project_manager().create_project("Test")

    def clean_up(self):
        if self.WrappedApp is None:
            return

        logging.info("Cleaning up Resolve...")

        project_manager = self.WrappedApp.get_project_manager()

        if not project_manager.get_current_project().get_name().startswith("Untitled Project"):
            try:
                logging.info("Saving current projet...")
                project_manager.save_current_project()
            except exceptions.ResolveAPIException:
                logging.fatal("Failed to save current project in Resolve.")
                sysexit()

        try:
            logging.info("Closing current project...")
            project_manager.close_current_project()
        except exceptions.ResolveAPIException:
            logging.info("Failed to close current project.")

        try:
            logging.info("Deleting 'Test' project...")
            project_manager.delete_project("Test")
        except exceptions.NotFoundException:
            logging.info("'Test' project could not be found.")


class UnsafeResolveAppTest(unittest.TestCase):
    Resolve: ResolveScriptAppContainer = None
    Assets = Path("../../tests/assets").absolute()


class SafeResolveAppTest(UnsafeResolveAppTest):
    @classmethod
    def setUpClass(cls) -> None:
        super(SafeResolveAppTest, cls).setUpClass()
        try:
            assert cls.Resolve.App is not None
        except AssertionError:
            raise unittest.SkipTest("Cannot access Resolve API.")

    @classmethod
    def media_pool(cls) -> resolve_api_mappings.ResolveMediaPoolHandler:
        return cls.Resolve.WrappedApp.get_current_project_media_pool()


class TestWithOneClip(SafeResolveAppTest):
    __slots__ = ["clip"]

    def setUp(self) -> None:
        self.clip: Optional[resolve_api_mappings.ResolveClipHandler] = None

    def tearDown(self) -> None:
        self.media_pool().remove_clips((self.clip,))

    def import_clip(self, file: Path):
        clips = self.media_pool().add_media_filepaths((file,))
        self.clip = clips.pop()
        return self.clip
