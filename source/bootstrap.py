#!/usr/bin/env python

"""
This file bootstraps the CatDV Importer source for DaVinci Resolve.
"""

import sys
import os
import logging

# as the script is running from the workspace -> scripts context menu,
# the "resolve" (resolve) and "fu" (fusion) global modules are passed into the script
# and therefore the DaVinciResolveScript does not need to be imported.

if sys.platform.startswith("darwin"):
    appDataDirectory = os.path.join(os.getenv("HOME"), "Library", "Application Support")
elif sys.platform.startswith("win") or sys.platform.startswith("cygwin"):
    appDataDirectory = os.getenv('LOCALAPPDATA')
elif sys.platform.startswith("linux"):
    try:
        appDataDirectory = os.getenv("XDG_DATA_HOME")
        assert appDataDirectory is not None
    except AssertionError:
        logging.info("'XDG_DATA_HOME' environment variable is not available, using ~/.local/share/ as appdata directory.")
        appDataDirectory = os.path.join(os.getenv("HOME"), ".local", "share")
else:
    try:
        appDataDirectory = os.getenv("LOCALAPPDATA")
        assert appDataDirectory is not None
    except AssertionError:
        logging.critical("Unrecognised OS. Please set the 'LOCALAPPDATA' environment variable to your app data directory.")
        sys.exit()

try:
    assert appDataDirectory is not None
except AssertionError:
    logging.critical("Unable to find app data directory. Try reinstalling.")
    sys.exit()

appPath = os.path.join(appDataDirectory, "CatDVResolve")


def activate_virtual_environment(environment_root):
    """Configures the virtual environment starting at ``environment_root``."""
    activate_script = os.path.join(environment_root, 'Scripts', 'activate_this.py')
    with open(activate_script) as activate_script_file:
        activate_script_code = compile(activate_script_file.read(), activate_script, "exec")
        exec(activate_script_code, {"__file__": activate_script})


activate_virtual_environment(os.path.join(appPath, "venv3.10"))
sys.path.insert(0, appPath)

from source.main import main

try:
    resolve
except NameError:
    resolve = None


if __name__ == "__main__":
    main(resolve)
