import sys
import logging
import webview
from pathlib import Path
from flask import Flask, request
import requests as fetch
from urllib.parse import urlparse, ParseResult

from webview_api import WebviewApi
from config import Config
from system_platform import Platform


lock_path = Path(".lock")
window_title = "DaVinci Resolve - CatDV Integration"


def check_for_app_already_running():
    if not lock_path.exists():
        return

    logging.fatal("Can not acquire app lock: App is already open!")
    import pygetwindow

    try:
        already_open_app = pygetwindow.getWindowsWithTitle(window_title)[0]
    except IndexError:
        logging.error("The lock exists, but the app doesn't seem to be open. Removing lock...")
        lock_path.unlink(missing_ok=True)
        return

    try:
        already_open_app.activate()
    except pygetwindow.PyGetWindowException:
        pass

    sys.exit(2)


def choose_web_renderer():
    system_platform = Platform.determine()

    if system_platform == Platform.Windows:
        return None

    if system_platform in (Platform.Linux, Platform.OSX):
        return "qt"

    import platform
    logging.warning(f"'{platform.system()}' is not recognised as a supported operating system.")

    return None


def make_web_server() -> Flask:
    server = Flask(__name__, static_folder="./static")

    @server.route("/")
    def _home():
        return server.redirect("/static/index.html")

    @server.route("/validate")
    def _validate():
        string_url_to_validate = request.args.get("url", default=None, type=str)
        if string_url_to_validate is None:
            return {"status": 400, "message": "Missing get-encoded URL parameter"}, 400

        try:
            url_to_validate = urlparse(string_url_to_validate)
        except ValueError:
            return {"status": 400, "message": "Invalid URL provided"}, 400

        if url_to_validate.scheme not in ("https", "http"):
            return {"status": 400, "message": "Provided URL's scheme is not HTTP/HTTPS"}, 400

        api_path = url_to_validate.path + ("" if url_to_validate.path.endswith("/") else "/") + "catdv/api/info"
        api_url = url_to_validate._replace(path=api_path)

        try:
            response = fetch.get(api_url.geturl())
        except fetch.exceptions.RequestException:
            return {"status": 200, "validation_result": False, "message": "Couldn't connect to specified host."}

        if not response.ok:
            return {"status": 200, "validation_result": False, "message": "Specified host is not a CatDV Server"}

        response_data = response.json()

        try:
            assert response_data["data"]["version"] is not None
            return {"status": 200, "validation_result": True, "message": "Success"}
        except (KeyError, AssertionError):
            return {"status": 200, "validation_result": False, "message": "Specified host should be a CatDV Server, but its software version could not be found"}

    return server


def main(resolve):
    logger = logging.getLogger(__name__)

    logger.info("Starting CatDV Panel...")
    logger.info('Python %s on %s' % (sys.version, sys.platform))

    webview_api_instance = WebviewApi(resolve)

    server = make_web_server()

    window = webview.create_window(window_title, server, js_api=webview_api_instance, background_color="#1e1e22")
    webview_api_instance.window = window

    check_for_app_already_running()

    def on_start():
        try:
            window.index_url = server.__webview_url
        except AttributeError as error:
            window.index_url = None
            logging.exception(error)

        try:
            saved_url = Config["saved_server_url"]
            logging.info("Loading saved CatDV server URL...")
            window.load_url(saved_url)
        except KeyError:
            pass

    try:
        lock_path.touch(exist_ok=False)
        webview.start(debug=logger.level <= logging.DEBUG, gui=choose_web_renderer(), func=on_start)
    finally:
        lock_path.unlink(missing_ok=True)
        Config.dump_to_file()


if __name__ == "__main__":
    main(None)
