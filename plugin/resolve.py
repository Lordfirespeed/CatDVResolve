import logging
from os import getcwd as working_directory
from contextlib import closing as contextlib_closing
from pathlib import Path
from functools import wraps
from uuid import uuid4 as random_uuid
from pathlib import Path
from enum import Enum
from defusedxml import ElementTree

from typing import Set

from plugin.exceptions import *


class DeletingFile:
    def __init__(self, file: Path):
        self.file = file

    def close(self):
        self.file.unlink()


class ResolveClipHandler:
    def __init__(self, resolve_media_pool_item):
        self.clip = resolve_media_pool_item

    def __eq__(self, other):
        if type(other) is not ResolveClipHandler:
            return False

        return self.clip == other.clip

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.clip)

    def get_name(self):
        return self.clip.GetName()

    def set_name(self, name):
        self.clip.SetClipProperty("Clip Name", name)

    def set_comment(self, comment):
        self.clip.SetMetadata("Comments", comment)

    def set_description(self, description):
        self.clip.SetMetadata("Description", description)

    def set_keywords(self, keywords: [str]):
        self.clip.SetMetadata("Keywords", ",".join(keywords))

    def add_marker(self, name, comment, in_frame, out_frame, colour):
        clip_start_frame = int(self.clip.GetClipProperty("Start"))

        if out_frame == -1:
            duration = 1
        else:
            duration = out_frame - in_frame

        frame_id = in_frame - clip_start_frame

        self.clip.AddMarker(frame_id, colour, name, comment, duration)


class ResolveTimelineItemHandler:
    def __init__(self, resolve_timeline_item):
        self.timeline_item = resolve_timeline_item

    def __eq__(self, other):
        if type(other) is not ResolveTimelineItemHandler:
            return False

        return self.timeline_item == other.timeline_item

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.timeline_item)

    def get_media_pool_item(self) -> ResolveClipHandler:
        resolve_media_pool_item = self.timeline_item.GetMediaPoolItem()

        if resolve_media_pool_item is None:
            raise ResolveAPIException

        return ResolveClipHandler(resolve_media_pool_item)


class ResolveTimelineHandler:

    class TrackType(Enum):
        Audio = "audio"
        Video = "video"
        Subtitle = "subtitle"

    def __init__(self, resolve_timeline):
        self.timeline = resolve_timeline

    def __eq__(self, other):
        if type(other) is not ResolveTimelineHandler:
            return False

        return self.timeline == other.timeline

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.timeline)

    def convert_to_compound_clip(self) -> ResolveTimelineItemHandler:
        resolve_timeline_item = self.timeline.CreateCompoundClip([item_handler.timeline_item for item_handler in self.get_all_timeline_items()])

        if resolve_timeline_item is None:
            try:
                video_one_items = self.get_item_track(self.TrackType.Video, 1)
                resolve_timeline_item_handler = video_one_items.pop()
            except IndexError:
                raise ResolveAPIException

            return resolve_timeline_item_handler

        return ResolveTimelineItemHandler(resolve_timeline_item)

    def get_all_item_tracks(self) -> [[ResolveTimelineItemHandler]]:
        tracks = []
        for track_type in self.TrackType:
            for track_index in range(1, self.get_track_count(track_type)+1):
                tracks.append(self.get_item_track(track_type, track_index))
        return tracks

    def get_all_timeline_items(self) -> [ResolveTimelineItemHandler]:
        return [item for track in self.get_all_item_tracks() for item in track]

    def get_all_media_items(self) -> Set[ResolveClipHandler]:
        media = set()
        for timeline_item in self.get_all_timeline_items():
            try:
                media.add(timeline_item.get_media_pool_item())
            except ResolveAPIException:
                continue
        return media

    def get_item_track(self, track_type: TrackType, track_index: int) -> [ResolveTimelineItemHandler]:
        resolve_timeline_items = self.timeline.GetItemListInTrack(track_type.value, track_index)
        return [ResolveTimelineItemHandler(item) for item in resolve_timeline_items]

    def get_track_count(self, track_type: TrackType) -> int:
        return self.timeline.GetTrackCount(track_type.value)


class ResolveFolderHandler:
    def __init__(self, resolve_folder):
        self.folder = resolve_folder

    def __eq__(self, other):
        if type(other) is not ResolveFolderHandler:
            return False

        return self.folder == other.folder

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.folder)

    def get_name(self) -> str:
        return self.folder.GetName()

    def get_clip_list(self) -> [ResolveClipHandler]:
        return [ResolveClipHandler(item) for item in self.folder.GetClipList()]

    def get_subfolder_list(self):
        return [ResolveFolderHandler(folder) for folder in self.folder.GetSubFolderList()]

    def get_subfolder_by_name(self, name: str):
        for subfolder in self.get_subfolder_list():
            if subfolder.get_name() == name:
                return subfolder
        raise NotFoundException


class ResolveMediaPoolHandler:
    def __init__(self, media_pool):
        self.pool = media_pool

    def __eq__(self, other):
        if type(other) is not ResolveFolderHandler:
            return False

        return self.pool == other.pool

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.pool)

    def get_root_folder(self) -> ResolveFolderHandler:
        return ResolveFolderHandler(self.pool.GetRootFolder())

    def add_subfolder(self, folder_parent: ResolveFolderHandler, name: str) -> ResolveFolderHandler:
        resolve_folder = self.pool.AddSubFolder(folder_parent.folder, name)

        if resolve_folder is None:
            raise ResolveAPIException

        return ResolveFolderHandler(resolve_folder)

    def get_current_folder(self) -> ResolveFolderHandler:
        resolve_folder = self.pool.GetCurrentFolder()

        if resolve_folder is None:
            raise ResolveAPIException

        return ResolveFolderHandler(resolve_folder)

    def set_current_folder(self, folder: ResolveFolderHandler) -> None:
        success = self.pool.SetCurrentFolder(folder.folder)

        if not success:
            raise ResolveAPIException

    def add_media_filepaths(self, filepaths: [Path]) -> [ResolveClipHandler]:
        new_media_pool_items = self.pool.ImportMedia([str(filepath) for filepath in filepaths])

        try:
            assert new_media_pool_items is not None
            assert len(new_media_pool_items) > 0
        except AssertionError:
            raise ResolveAPIException

        logging.debug(f"New Media Pool Items: {new_media_pool_items}")
        return [ResolveClipHandler(item) for item in new_media_pool_items]

    def add_xml_timeline(self, filepath: Path) -> ResolveTimelineHandler:
        logging.debug(f"Importing XML file '{str(filepath)}'")
        new_timeline = self.pool.ImportTimelineFromFile(str(filepath))

        if new_timeline is None:
            raise ResolveAPIException(f"No timeline created from path '{str(filepath)}'")

        return ResolveTimelineHandler(new_timeline)

    def move_clips(self, clips: [ResolveClipHandler], target: ResolveFolderHandler) -> None:
        success = self.pool.MoveClips([clip_handler.clip for clip_handler in clips], target.folder)

        if not success:
            raise ResolveAPIException

    def remove_clips(self, clips: [ResolveClipHandler]):
        self.pool.DeleteClips([clip_handler.clip for clip_handler in clips])

    def remove_timelines(self, timelines: [ResolveTimelineHandler]):
        self.pool.DeleteTimelines([timeline_handler.timeline for timeline_handler in timelines])


class ResolveApiJsonHandler:
    simple_clip_types = ["clip", "still", "audio"]
    complex_clip_types = ["subclip", "seq"]
    default_marker_colour = "Blue"
    compound_sources_bin_name = "CatDV Compound Sources"

    def __init__(self, resolve):
        self.resolve = resolve
        self.marker_colour = self.default_marker_colour

    class Decorators:
        @staticmethod
        def redirect_key_errors(method):
            @wraps(method)
            def wrap_method(*args, **kwargs):
                try:
                    return method(*args, **kwargs)
                except KeyError:
                    raise JSONException

            return wrap_method

        @staticmethod
        def ignore_key_errors(method):
            @wraps(method)
            def wrap_method(*args, **kwargs):
                try:
                    return method(*args, **kwargs)
                except KeyError:
                    return

            return wrap_method

    @staticmethod
    def get_clip_media_path(clip_data: {}) -> Path:
        try:
            media_field = clip_data["media"]
            assert type(media_field) is dict
            filepath_string = media_field["filePath"]
        except (KeyError, AssertionError):
            raise JSONException

        try:
            filepath = Path(filepath_string)  # raises TypeError if filepath string is None
        except TypeError:
            raise JSONException

        if not filepath.is_file():
            raise OSError

        return filepath

    def add_single_clip_to_media_pool(self, clip_data: {}, media_pool) -> ResolveClipHandler:
        filepath = self.get_clip_media_path(clip_data)
        return media_pool.add_media_filepaths([filepath])[0]

    def add_marker_to_pool_item(self, marker_data: {}, clip: ResolveClipHandler):
        try:
            name = marker_data["name"]
            assert type(name) is str
        except (KeyError, AssertionError):
            raise JSONException

        try:
            comment = marker_data["description"]
            assert type(comment) is str
        except (KeyError, AssertionError):
            raise JSONException

        try:
            in_data = marker_data["in"]
            assert type(in_data) is dict
            in_frame = in_data["frm"]
            assert type(in_frame) is int
        except (KeyError, AssertionError):
            raise JSONException

        try:
            out_data = marker_data["out"]
            try:
                assert type(out_data) is dict
                out_frame = out_data["frm"]
                assert type(out_frame) is int
            except (KeyError, AssertionError):
                raise JSONException
        except KeyError:
            out_frame = -1

        clip.add_marker(name, comment, in_frame, out_frame, self.marker_colour)

    def add_all_markers_to_pool_item(self, clip_data: {}, clip: ResolveClipHandler):
        try:
            marker_list = clip_data["markers"]
        except KeyError:
            return

        for marker_data in marker_list:
            self.add_marker_to_pool_item(marker_data, clip)

    @Decorators.redirect_key_errors
    def set_pool_item_name(self, clip_data: {}, clip: ResolveClipHandler):
        name = clip_data["name"]
        clip.set_name(name)

    @Decorators.redirect_key_errors
    def set_pool_item_description(self, clip_data: {}, clip: ResolveClipHandler):
        description = f"CatDV Asset ID: {clip_data['ID']}"
        clip.set_description(description)

    @Decorators.ignore_key_errors
    def set_pool_item_comment(self, clip_data: {}, clip: ResolveClipHandler):
        comment = clip_data["notes"]

        if comment is None:
            return

        clip.set_comment(comment)

    def populate_pool_item_metadata(self, clip_data: {}, clip: ResolveClipHandler):
        self.set_pool_item_name(clip_data, clip)
        self.set_pool_item_description(clip_data, clip)
        self.set_pool_item_comment(clip_data, clip)
        self.add_all_markers_to_pool_item(clip_data, clip)
        clip.set_keywords([])

    def get_media_pool(self):
        project_manager = self.resolve.GetProjectManager()
        current_project = project_manager.GetCurrentProject()
        return ResolveMediaPoolHandler(current_project.GetMediaPool())

    def import_simple_json_clip(self, clip_data: {}, media_pool=None) -> ResolveClipHandler:
        if media_pool is None:
            media_pool = self.get_media_pool()

        media_pool_item = self.add_single_clip_to_media_pool(clip_data, media_pool)

        try:
            self.populate_pool_item_metadata(clip_data, media_pool_item)
        except Exception as error:
            media_pool.remove_clips([media_pool_item])
            raise error

        return media_pool_item

    def create_compound_sources_bin(self, media_pool=None) -> ResolveFolderHandler:
        if media_pool is None:
            media_pool = self.get_media_pool()

        return media_pool.add_subfolder(media_pool.get_root_folder(), self.compound_sources_bin_name)

    def get_compound_sources_bin(self, media_pool=None) -> ResolveFolderHandler:
        if media_pool is None:
            media_pool = self.get_media_pool()

        try:
            return media_pool.get_root_folder().get_subfolder_by_name(self.compound_sources_bin_name)
        except NotFoundException:
            return self.create_compound_sources_bin()

    def import_complex_json_clip_to_timeline(self, clip_data: {}, media_pool=None) -> ResolveTimelineHandler:
        if media_pool is None:
            media_pool = self.get_media_pool()

        try:
            xml_content = clip_data["subclip.xml"]
        except KeyError:
            raise JSONException("FCPXML field could not be found.")

        temporary_xml_filepath = Path("temp", f"{random_uuid()}.xml")

        with open(temporary_xml_filepath, "w") as temporary_xml_file:
            temporary_xml_file.write(xml_content)

        with contextlib_closing(DeletingFile(temporary_xml_filepath)):
            return media_pool.add_xml_timeline(Path(working_directory(), temporary_xml_filepath))

    def import_complex_json_clip(self, clip_data: {}, media_pool: ResolveMediaPoolHandler=None) -> ResolveClipHandler:
        if media_pool is None:
            media_pool = self.get_media_pool()

        # get the target import folder
        importing_to = media_pool.get_current_folder()
        # set the current folder to the compound sources bin
        compound_sources_bin = self.get_compound_sources_bin()
        media_pool.set_current_folder(compound_sources_bin)
        # import the timeline to the media pool via a temporary XML file
        timeline = self.import_complex_json_clip_to_timeline(clip_data, media_pool)
        # convert the timeline to a compound clip, get the media pool item
        created_clip = timeline.convert_to_compound_clip().get_media_pool_item()
        # remove the timeline
        media_pool.remove_timelines([timeline])
        # move the imported item back to the target folder
        media_pool.move_clips([created_clip], importing_to)
        # set the view to the import folder
        media_pool.set_current_folder(importing_to)
        return created_clip

    def import_single_json_clip(self, clip_data: {}, media_pool=None) -> ResolveClipHandler:
        if media_pool is None:
            media_pool = self.get_media_pool()

        try:
            assert type(clip_data) is dict
        except AssertionError:
            raise JSONException

        try:
            if clip_data["type"] in self.simple_clip_types:
                return self.import_simple_json_clip(clip_data, media_pool)

            if clip_data["type"] in self.complex_clip_types:
                return self.import_complex_json_clip(clip_data, media_pool)

            raise NotImplementedError

        except KeyError:
            raise JSONException

    def import_json_media(self, media_data: [], media_pool=None) -> [ResolveClipHandler]:
        if media_pool is None:
            media_pool = self.get_media_pool()

        try:
            clip_element_list = media_data
            assert type(clip_element_list) is list
        except AssertionError:
            raise JSONException

        logging.debug(f"Received clips JSON: {clip_element_list}")

        pool_items = []

        for clip_json in clip_element_list:
            try:
                pool_items.append(self.import_single_json_clip(clip_json, media_pool))
            except (ResolveAPIException, JSONException, OSError, NotImplementedError) as error:
                pool_items.append(error)
                logging.exception(error)

        return pool_items
