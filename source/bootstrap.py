#!/usr/bin/env python

"""
This file bootstraps the CatDV Importer source for DaVinci Resolve.
"""

import sys
import os
import logging
from pathlib import Path

# as the script is running from the workspace -> scripts context menu,
# the "resolve" (resolve) and "fu" (fusion) global modules are passed into the script
# and therefore the DaVinciResolveScript does not need to be imported.

if sys.platform.startswith("darwin"):
    appPath = Path("/", "Library", "Application Support", "Square Box", "CatDV-Resolve")
elif sys.platform.startswith("win") or sys.platform.startswith("cygwin"):
    appPath = Path(os.getenv('PROGRAMFILES'), "CatDV-Resolve")
elif sys.platform.startswith("linux"):
    appPath = Path("/", "opt", "catdv-resolve")
    # appPath = Path("/", "home", "joeclack", "PycharmProjects", "CatDVResolve")
else:
    try:
        appPath = os.getenv("CATDVRESOLVEAPP")
        assert appPath is not None
    except AssertionError:
        logging.critical("Unrecognised OS. Please set the 'CATDVRESOLVEAPP' environment variable to your app data directory.")
        sys.exit()

try:
    assert appPath is not None
except AssertionError:
    logging.critical("Unable to find app data directory. Try reinstalling.")
    sys.exit()


def activate_virtual_environment(environment_root):
    """Configures the virtual environment starting at ``environment_root``."""
    if sys.platform.startswith("win"):
        activate_script = Path(environment_root, 'Scripts', 'activate_this.py')
    else:
        activate_script = Path(environment_root, "bin", "activate_this.py")

    with open(activate_script) as activate_script_file:
        activate_script_code = compile(activate_script_file.read(), activate_script, "exec")
        exec(activate_script_code, {"__file__": activate_script})


activate_virtual_environment(os.path.join(appPath, "venv"))
sys.path.insert(0, str(appPath))
print(sys.path)

from source.main import main

try:
    resolve
except NameError:
    resolve = None


if __name__ == "__main__":
    main(resolve)
