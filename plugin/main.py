import logging
import traceback
from json import loads as json_load_string
from json.decoder import JSONDecodeError
from pathlib import Path

from plugin.exceptions import *
from plugin.resolve import ResolveApiJsonHandler


class WebviewApi:
    error_messages = {
        ResolveAPIException: "Some items' could not be added to media pool, no reason given by Resolve API.",
        JSONException: "Some items' JSON was invalid, leading to incomplete media import or metadata.",
        OSError: "Some items could not be found in the filesystem.",
        NotImplementedError: "Some items were not on local storage, or were not masterclips. These features are not implemented."
    }

    def __init__(self, resolve):
        """Create a new WebviewApi from Resolve API's 'Resolve' object."""
        self.resolve_handler = ResolveApiJsonHandler(resolve)

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
        except JSONException:
            return self._log_and_return(logging.error, "Invalid JSON Provided.")
        except Exception as error:
            logging.exception(error)
            return "Encountered unexpected exception.\n" + "".join(traceback.format_exception(type(error), error, error.__traceback__))

        error_message_stack = []
        for error_type, error_message in self.error_messages.items():
            if any([type(clip) == error_type for clip in new_clips]):
                error_message_stack.append(error_message)

        if len(error_message_stack) > 0:
            concatenated_error_message = "\n".join(error_message_stack)
            return self._log_and_return(logging.error, f"Some items may have been imported successfully, however:\n{concatenated_error_message}")

        return self._log_and_return(logging.info, "Successfully added item(s) to media pool.")

