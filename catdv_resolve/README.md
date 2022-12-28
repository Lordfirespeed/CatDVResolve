# Installation
## Server
Ensure that your CatDV server is sufficiently up-to-date (>=10.1.4).

## Client
### Prerequisite: Python 3
For DaVinci Resolve 16 / 17:
- Install [Python 3.6](https://www.python.org/downloads/release/python-368/)

For DaVinci Resolve 18:
- Install any version of Python from 3.6 through 3.10 ([Downloads](https://www.python.org/downloads))
- Preferably, the latest version of [Python 3.10](https://www.python.org/downloads/release/python-3109/)

*Note: All downloads are at the bottom of linked pages. Scroll down!*
### Module
Open a new terminal window. 

1) Ensure you are executing the intended python version:
    ```bash
    python3 --version
2) Optional step:

   Install the wheel package to utilise Python's newer package install methods.
   ```bash
   pip3 install wheel
   ```
3) Install the package:
    ```bash
    pip3 install catdv_resolve
    ```
4) Finalise the installation:
    ```bash
    python3 -m catdv_resolve install
    ```
    (This step creates a symbolic link so that DaVinci Resolve can find the plugin's files).

For advanced users: [Advanced Installation](#advanced-installation)

# Usage
In DaVinci Resolve, 
- Select `Workspace` from the toolbar at the top of the window;
- select the `Scripts` option from the drop-down (near the bottom); 
- Choose `CatDV` to open the plugin's panel.
- You will be prompted to enter the URL for your CatDV Web Panel.
- Login to your account using the `Login` button located at the top-right.

# Upgrade
Sometimes new versions of the software may be released; to upgrade the installed version of the panel, use 
a terminal to execute the following commands:
1) ```bash
   pip3 install --upgrade catdv_resolve
   ```
2) ```bash
   python3 -m catdv_resolve install --force
   ```

# Advanced Installation
The package can also be installed into a Python virtual environment (`venv`) of the appropriate Python version.
1) Ensure you are executing the intended python version:
    ```bash
    python3 --version
    ```
2) Create a new `venv` using the Virtualenv tool:
    ```bash
    python3 -m venv [target]
    ```
    E.g. `python3 -m venv ./venv310` is an ideal choice for a Python 3.10 `venv`.

    Following instructions assume the `target` provided was `./venv310`.
3) Activate the `venv`:
    #### Windows
    ```cmd
    .\venv310\Scripts\activate.bat
    ```
    #### Mac / Linux / *nix
    ```bash
    source ./venv310/bin/activate
    ```
4) Optional step:

   Install the wheel package to utilise Python's newer package install methods.
   ```bash
   pip3 install wheel
   ```
5) Install the package:
    ```bash
    pip3 install catdv_resolve
    ```
6) Finalise the installation:
    ```bash
    python3 -m catdv_resolve install
    ```
    (This step creates a symbolic link so that DaVinci Resolve can find the plugin's files).
    