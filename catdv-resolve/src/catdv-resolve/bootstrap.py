#!/usr/bin/env python

"""
This file bootstraps the CatDV Importer source for DaVinci Resolve.
"""

import sys
import os
import logging
import platform
from pathlib import Path

# as the script is running from the workspace -> scripts context menu,
# the "resolve" (resolve) and "fu" (fusion) global modules are passed into the script
# and therefore the DaVinciResolveScript does not need to be imported.


def get_script_symlink_path() -> Path:
    return Path(sys.argv[0])


def get_app_directory() -> Path:
    script_actual_path = Path(get_script_symlink_path()).resolve()
    return script_actual_path.parent


def get_data_directory() -> Path:
    scripts_dir = get_script_symlink_path().parent.parent
    davinci_dir = scripts_dir.parent.parent
    data_dir = Path(davinci_dir, "CatDV")
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_environment_root() -> Path:
    system_name = platform.system()
    if system_name == "Windows":
        return get_app_directory().parent.parent.parent
    else:
        return get_app_directory().parent.parent.parent.parent


def activate_virtual_environment(environment_root: Path):
    """Configures the (virtual) environment starting at ``environment_root``."""

    system_name = platform.system()
    if system_name == "Windows":
        site_packages = Path(environment_root, 'Lib', 'site-packages')
    else:
        site_packages = Path(environment_root, 'lib', 'python%s' % sys.version[:3], 'site-packages')
    prev_sys_path = list(sys.path)
    import site
    site.addsitedir(str(site_packages))

    # Move the added items to the front of the path:
    new_sys_path = []
    for item in list(sys.path):
        if item not in prev_sys_path:
            new_sys_path.append(item)
            sys.path.remove(item)
    sys.path[:0] = new_sys_path


debug_venv_root = os.getenv("DEBUG_CATDV_RESOLVE_VENV")
app_path = get_app_directory()
data_path = get_data_directory()

os.chdir(data_path)

logging_level = os.getenv("CATDV_RESOLVE_LOGGING_LEVEL")  # should be an integer https://docs.python.org/3/library/logging.html#logging-levels

if not logging_level:
    logging_level = logging.INFO

logging.basicConfig(
    level=logging_level,
    filename="_latest.log",
    filemode="w",
    format="%(levelname)s %(asctime)s - %(message)s"
)

if debug_venv_root:
    logging.debug(f"Activating DEBUG virtual env at `{debug_venv_root}`")
    activate_virtual_environment(Path(debug_venv_root))
else:
    activate_virtual_environment(get_environment_root())

sys.path.insert(0, str(app_path))

from main import main

try:
    resolve
except NameError:
    resolve = None


if __name__ == "__main__":
    main(resolve)
