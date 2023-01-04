from __future__ import annotations
import argparse
import sys
from pathlib import Path
import logging
from os import symlink as os_symlink

from .system_platform import Platform


class Installer:
    def __init__(self, args: argparse.Namespace) -> None:
        self.system_platform = Platform.determine()
        self.args = args

    def request_admin_escalation_or_exit(self):
        if self.system_platform != Platform.Windows:
            return

        # https://stackoverflow.com/a/72732324/11045433 BaiJiFeiLong
        from ctypes import windll
        if windll.shell32.IsUserAnAdmin():
            return

        if sys.argv[0].endswith("exe"):
            sys.exit()

        returncode = windll.shell32.ShellExecuteW(None, "runas", sys.executable, "-m catdv_resolve " + " ".join(sys.argv[1:]) + " --uac_escalated", None, 1)
        success = returncode > 32

        if not success:
            logging.fatal("UAC escalation was declined. Admin priveleges are needed to install globally.")

        sys.exit()

    def get_linux_resolve_dir(self) -> Path:
        if self.system_platform != Platform.Linux:
            raise OSError

        opt_path = Path("/", "opt", "resolve").resolve()
        home_path = Path("/", "home", "resolve").resolve()

        if home_path.is_dir():
            return home_path
        else:
            return opt_path

    def get_resolve_system_scripts_directory(self) -> Path:
        if self.system_platform == Platform.OSX:
            return Path("/", "Library", "Application Support", "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts")
        elif self.system_platform == Platform.Linux:
            return Path(self.get_linux_resolve_dir(), "Fusion", "Scripts")
        elif self.system_platform == Platform.Windows:
            from os import getenv as osgetenv
            return Path(osgetenv("PROGRAMDATA"), "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts")
        else:
            raise NotImplementedError("Unsupported platform; can't find DaVinci Resolve's Scripts directory.")

    def get_resolve_user_scripts_directory(self) -> Path:
        from os import getenv as osgetenv
        if self.system_platform == Platform.OSX:
            return Path(osgetenv("HOME"), "Library", "Application Support", "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts")
        elif self.system_platform == Platform.Linux:
            return Path(osgetenv("HOME"), ".local", "share", "DaVinciResolve", "Fusion", "Scripts")
        elif self.system_platform == Platform.Windows:
            return Path(osgetenv("APPDATA"), "Blackmagic Design", "DaVinci Resolve", "Support", "Fusion", "Scripts")
        else:
            raise NotImplementedError("Unsupported platform; can't find DaVinci Resolve's Scripts directory.")

    @staticmethod
    def get_package_directory():
        return Path(__file__).resolve().parent

    def install_plugin_symlink(self) -> None:
        scripts_directory = self.get_resolve_system_scripts_directory()

        if self.args.one_user:
            scripts_directory = Path(self.get_resolve_user_scripts_directory())

        symlink_destination = Path(scripts_directory, "Utility", "CatDV.py")

        if not symlink_destination.parent.is_dir():
            raise OSError("DaVinci Resolve Scripts folder could not be found. Is DaVinci Resolve installed?")

        if symlink_destination.is_file():
            if not self.args.force:
                raise OSError("CatDV Resolve plugin is already installed. Use --force to overwrite old installation.")

            symlink_destination.unlink()

        try:
            os_symlink(Path(self.get_package_directory(), "bootstrap.py"), symlink_destination)
        except OSError:
            self.request_admin_escalation_or_exit()

        logging.info("CatDV plugin has been successfully installed!")
        self.prevent_opened_shell_from_closing()

    def execute(self) -> None:
        try:
            self.args.target_function
        except AttributeError:
            parser.error("No command specified")
            sys.exit(2)

        try:
            self.__getattribute__(self.args.target_function)()
        except Exception as error:
            logging.fatal(error)
            logging.error("An unexpected error occurred.")
            self.prevent_opened_shell_from_closing()
            sys.exit(2)

    def prevent_opened_shell_from_closing(self):
        if not self.args.uac_escalated:
            return

        input("Press Enter to continue; ")


class ParserThatGivesUsageOnError(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        sys.stderr.write(f"Error: {message}\n")
        self.print_help()
        sys.exit(2)


logging.basicConfig(level=logging.INFO)


parser = ParserThatGivesUsageOnError(description="Use the CatDV Resolve Plugin command-line tool.")
subparsers = parser.add_subparsers(
    title="commands",
    metavar="[command]",
    help="description"
)

install_parser = subparsers.add_parser("install", help="install the plugin")
install_parser.add_argument("--uac_escalated", action="store_true", help=argparse.SUPPRESS)
install_parser.add_argument("--one_user", action="store_true", help="Install for the current user only.")
install_parser.add_argument("-f", "--force", action="store_true", help="Force install (overwrite old installations)")
install_parser.set_defaults(target_function="install_plugin_symlink")

args = parser.parse_args()

installer_instance = Installer(args)
installer_instance.execute()
