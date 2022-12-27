import sys
import logging
import webview
from pathlib import Path
from flask import Flask

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


def main(resolve):
    logger = logging.getLogger(__name__)

    logger.info("Starting CatDV Panel...")
    logger.info('Python %s on %s' % (sys.version, sys.platform))

    webview_api_instance = WebviewApi(resolve)

    server = Flask(__name__, static_folder="./static")

    @server.route("/", methods=["GET"])
    def _():
        return server.redirect("/static/index.html")

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
