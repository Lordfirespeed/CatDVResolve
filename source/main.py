import os
import sys
import logging
import webview
from source.webview_api import WebviewApi
from pathlib import Path


def get_app_directory():
    return Path(__file__).resolve().parent.parent


def main(resolve):
    app_path = get_app_directory()
    os.chdir(app_path)

    log_file_path = Path(app_path, "_latest.log")
    logging.basicConfig(level=logging.DEBUG, filename=log_file_path, filemode="w", format="%(levelname)s %(asctime)s - %(message)s")

    logging.info('Python %s on %s' % (sys.version, sys.platform))

    webview_api = WebviewApi(resolve)

    window = webview.create_window("DaVinci Resolve - CatDV Integration", "assets/index.html", js_api=webview_api, background_color="#1f1f1f")
    webview_api.window = window

    webview.start(debug=True)
