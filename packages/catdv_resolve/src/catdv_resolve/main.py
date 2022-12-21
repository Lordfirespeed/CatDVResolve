import sys
import logging
import webview
from pathlib import Path
from webview_api import WebviewApi
from flask import Flask


lock_path = Path(".lock")


def main(resolve):
    logger = logging.getLogger("root")

    logger.info("Starting ")
    logger.info('Python %s on %s' % (sys.version, sys.platform))
    logger.info("henlo")

    webview_api_instance = WebviewApi(resolve)

    server = Flask(__name__, static_folder="./static")

    @server.route("/", methods=["GET"])
    def _():
        return server.redirect("/static/index.html")

    window = webview.create_window("DaVinci Resolve - CatDV Integration", server, js_api=webview_api_instance, background_color="#1f1f1f")
    webview_api_instance.window = window

    if lock_path.exists():
        logging.fatal("Can not acquire app lock: App is already open!")
        sys.exit(2)

    try:
        lock_path.touch(exist_ok=False)
        webview.start(debug=logger.level <= logging.DEBUG)
    finally:
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main(None)
