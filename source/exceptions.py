class ExceptionWithMessage(Exception):
    def __init__(self, message=None):
        if message is None:
            message = ""
        self.message = message


class JSONException(ExceptionWithMessage):
    """Exception raised for errors relating to the received JSON data."""
    pass


class ResolveAPIException(ExceptionWithMessage):
    """Exception raised for errors relating to the Resolve API, usually when the API returns False or None."""
    pass


class NotFoundException(ExceptionWithMessage):
    """Exception raised for errors relating to searches and such like returning no matches."""
    pass
