from typing import Optional
import logging
import unittest
from pathlib import Path
from sys import exit as sysexit

from source import exceptions


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
            wrapped_app = source.resolve.ResolveHandler(resolve_app)
        except AssertionError:
            wrapped_app = None

        self.Script = resolve_script
        self.App = resolve_app
        self.WrappedApp = wrapped_app

    def set_up(self):
        if self.WrappedApp is None:
            return

        print("Beginning Resolve setup...")

        self.clean_up()

        self.WrappedApp.get_project_manager().create_project("Test")

    def clean_up(self):
        if self.WrappedApp is None:
            return

        print("Cleaning up Resolve...")

        project_manager = self.WrappedApp.get_project_manager()

        if not project_manager.get_current_project().get_name().startswith("Untitled Project"):
            try:
                print("Saving current projet...")
                project_manager.save_current_project()
            except exceptions.ResolveAPIException:
                logging.fatal("Failed to save current project in Resolve.")
                sysexit()

        try:
            print("Closing current project...")
            project_manager.close_current_project()
        except exceptions.ResolveAPIException:
            print("Failed to close current project.")

        try:
            print("Deleting 'Test' project...")
            project_manager.delete_project("Test")
        except exceptions.NotFoundException:
            print("'Test' project could not be found.")


class UnsafeResolveAppTest(unittest.TestCase):
    Resolve: ResolveScriptAppContainer = None
    Assets = Path("assets").absolute()


class SafeResolveAppTest(UnsafeResolveAppTest):
    @classmethod
    def setUpClass(cls) -> None:
        super(SafeResolveAppTest, cls).setUpClass()
        try:
            assert cls.Resolve.App is not None
        except AssertionError:
            raise unittest.SkipTest("Cannot access Resolve API.")

    @classmethod
    def media_pool(cls) -> source.resolve.ResolveMediaPoolHandler:
        return cls.Resolve.WrappedApp.get_current_project_media_pool()


class TestWithOneClip(SafeResolveAppTest):
    __slots__ = ["clip"]

    def setUp(self) -> None:
        self.clip: Optional[source.resolve.ResolveClipHandler] = None

    def tearDown(self) -> None:
        self.media_pool().remove_clips((self.clip,))

    def import_clip(self, file: Path):
        clips = self.media_pool().add_media_filepaths((file,))
        self.clip = clips.pop()
        return self.clip
