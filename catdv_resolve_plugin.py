import logging
from pathlib import Path
from functools import wraps
from json import loads as json_load_string
from json.decoder import JSONDecodeError


class JSONException(Exception):
    """Exception raised for errors relating to the received JSON data."""
    pass


class ResolveAPIException(Exception):
    """Exception raised for errors relating to the Resolve API, usually when the API returns False or None."""
    pass


class ResolveClipHandler:
    def __init__(self, resolve_media_pool_item):
        self.clip = resolve_media_pool_item

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


class ResolveApiJsonHandler:
    accepted_clip_types = ["clip", "still", "audio"]
    default_marker_colour = "Blue"

    def __init__(self, resolve):
        self.resolve = resolve
        self.marker_colour = self.default_marker_colour

    class Decorators:
        @staticmethod
        def catch_json_exceptions(method):
            @wraps(method)
            def wrap_method(*args, **kwargs):
                try:
                    return method(*args, **kwargs)
                except KeyError:
                    raise JSONException

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

    @staticmethod
    def add_media_filepaths_to_media_pool(filepaths: [Path], media_pool) -> [ResolveClipHandler]:
        new_media_pool_items = media_pool.ImportMedia([str(filepath) for filepath in filepaths])

        try:
            assert new_media_pool_items is not None
            assert len(new_media_pool_items) > 0
        except AssertionError:
            raise ResolveAPIException

        logging.debug(f"New Media Pool Items: {new_media_pool_items}")
        return [ResolveClipHandler(item) for item in new_media_pool_items]

    @staticmethod
    def remove_clips_from_media_pool(clips: [ResolveClipHandler], media_pool):
        media_pool.DeleteClips([clip_handler.clip for clip_handler in clips])

    @staticmethod
    def add_clip_to_media_pool(clip_data: {}, media_pool) -> ResolveClipHandler:
        filepath = ResolveApiJsonHandler.get_clip_media_path(clip_data)
        return ResolveApiJsonHandler.add_media_filepaths_to_media_pool([filepath], media_pool)[0]

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
            raise JSONException

        for marker_data in marker_list:
            self.add_marker_to_pool_item(marker_data, clip)

    @Decorators.catch_json_exceptions
    def set_pool_item_name(self, clip_data: {}, clip: ResolveClipHandler):
        name = clip_data["name"]
        clip.set_name(name)

    @Decorators.catch_json_exceptions
    def set_pool_item_description(self, clip_data: {}, clip: ResolveClipHandler):
        description = f"CatDV Asset ID: {clip_data['ID']}"
        clip.set_description(description)

    @Decorators.catch_json_exceptions
    def set_pool_item_comment(self, clip_data: {}, clip: ResolveClipHandler):
        comment = clip_data["notes"]

        if comment is None:
            return

        clip.set_comment(comment)

    def populate_pool_item_metadata(self, clip_data: {}, clip: ResolveClipHandler):
        self.add_all_markers_to_pool_item(clip_data, clip)
        self.set_pool_item_name(clip_data, clip)
        self.set_pool_item_description(clip_data, clip)
        self.set_pool_item_comment(clip_data, clip)
        clip.set_keywords([])

    def get_media_pool(self):
        project_manager = self.resolve.GetProjectManager()
        current_project = project_manager.GetCurrentProject()
        return current_project.GetMediaPool()

    def import_single_json_clip(self, clip_data: {}, media_pool=None) -> ResolveClipHandler:
        if media_pool is None:
            media_pool = self.get_media_pool()

        try:
            assert type(clip_data) is dict
        except AssertionError:
            raise JSONException

        try:
            assert clip_data["type"] in self.accepted_clip_types
        except KeyError:
            raise JSONException
        except AssertionError:
            raise NotImplementedError

        media_pool_item = self.add_clip_to_media_pool(clip_data, media_pool)

        try:
            self.populate_pool_item_metadata(clip_data, media_pool_item)
        except Exception as error:
            self.remove_clips_from_media_pool(media_pool_item, media_pool)
            raise error

        return media_pool_item

    def import_json_media(self, media_data: {}, media_pool=None) -> [ResolveClipHandler]:
        if media_pool is None:
            media_pool = self.get_media_pool()

        try:
            clip_element_list = media_data["items"]
            assert type(clip_element_list) is list
        except KeyError:
            raise JSONException

        pool_items = []

        for clip_json in clip_element_list:
            try:
                pool_items.append(self.import_single_json_clip(clip_json, media_pool))
            except (ResolveAPIException, JSONException, OSError, NotImplementedError) as error:
                pool_items.append(error)

        return pool_items


class WebviewApi:
    error_messages = {
        ResolveAPIException: "Some items' could not be added to media pool, no reason given by Resolve API.",
        JSONException: "Some items' JSON was invalid, leading to incomplete media import or metadata.",
        OSError: "Some items could not be found in the filesystem.",
        NotImplementedError: "Some items were not masterclips. These features are not implemented."
    }

    def __init__(self, resolve_handler: ResolveApiJsonHandler):
        self.resolve_handler = resolve_handler

    @staticmethod
    def _log_and_return(level, message):
        level(message)
        return {"message": message}

    def import_json_clips(self, json_string):
        try:
            data = json_load_string(json_string)
        except JSONDecodeError:
            return self._log_and_return(logging.error, "Invalid JSON Provided.")

        try:
            new_clips = self.resolve_handler.import_json_media(data)
        except Exception as error:
            logging.exception(error)
            return self._log_and_return(logging.error, "Encountered unexpected exception.")

        error_message_stack = []
        for error_type, error_message in self.error_messages.items():
            if any([type(clip) == error_type for clip in new_clips]):
                error_message_stack.append(error_message)

        if len(error_message_stack) > 0:
            concatenated_error_message = "\n".join(error_message_stack)
            return self._log_and_return(logging.error, f"Some items may have been imported successfully, however:\n{concatenated_error_message}")

        return self._log_and_return(logging.info, "Successfully added item(s) to media pool.")

