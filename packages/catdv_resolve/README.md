# Installation
## Server
Ensure that your CatDV server is sufficiently up-to-date (>=10.1.4).

## Client
### Prerequisite: Python
For DaVinci Resolve 16 / 17:
Install 

### Module
Once the module has been installed using
```bash
pip install catdv_resolve
```
Use the command
```bash
python -m catdv_resolve install
```
to finalise installation (create a symbolic link so that DaVinci Resolve can find the plugin's files).

# Usage
In DaVinci Resolve, 
- Select `Workspace` from the toolbar at the top of the window;
- select the `Scripts` option from the drop-down (near the bottom); 
- Choose `CatDV` to open the plugin's panel.
- You will be prompted to enter the URL for your CatDV Web Panel.
- Login to your account using the `Login` button located at the top-right.