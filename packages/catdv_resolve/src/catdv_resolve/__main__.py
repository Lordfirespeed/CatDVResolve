from __future__ import annotations
import argparse
import sys
from pathlib import Path
import logging
from os import symlink as os_symlink
from enum import Enum, auto


class Platform(Enum):
    Unknown = auto()
    OSX = auto()
    Linux = auto()
    Windows = auto()

    @classmethod
    def determine(cls) -> Platform:
        import platform
        system_name = platform.system()
        if system_name == "Darwin":
            return cls.OSX
        elif system_name == "Linux":
            return cls.Linux
        elif system_name == "Windows":
            return cls.Windows
        else:
            return cls.Unknown


class Installer:
    def __init__(self, args: argparse.Namespace) -> None:
        self.system_platform = Platform.determine()
        self.args = args

    def request_admin_escalation_or_exit(self):
        if self.system_platform != Platform.Windows:
            return

        from ctypes import windll
        if windll.shell32.IsUserAnAdmin():
            return

        if not sys.argv[0].endswith("exe"):
            success = windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv) + " --uac_escalated", None, 1) > 32

        sys.exit()

    def get_linux_resolve_dir(self) -> Path:
        if self.system_platform != Platform.Linux:
            raise OSError

        opt_path = Path("opt", "resolve").resolve()
        home_path = Path("home", "resolve").resolve()

        if home_path.is_dir():
            return home_path
        else:
            return opt_path

    def get_resolve_system_scripts_directory(self) -> Path:
        if self.system_platform == Platform.OSX:
            return Path("Library", "Application Support", "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts")
        elif self.system_platform == Platform.Linux:
            return Path(self.get_linux_resolve_dir(), "Fusion", "Scripts")
        elif self.system_platform == Platform.Windows:
            from os import getenv as osgetenv
            return Path(osgetenv("PROGRAMDATA"), "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts")
        else:
            raise NotImplementedError("Unsupported platform; can't find DaVinci Resolve's Scripts directory.")

    @staticmethod
    def get_package_directory():
        return Path(__file__).resolve().parent

    def install_plugin_symlink(self) -> None:
        self.request_admin_escalation_or_exit()

        symlink_destination = Path(self.get_resolve_system_scripts_directory(), "Utility", "CatDV-Resolve.py")
        symlink_destination.unlink(missing_ok=True)

        os_symlink(Path(self.get_package_directory(), "bootstrap.py"), symlink_destination)

        logging.info("CatDV plugin has been successfully installed!")
        self.prevent_opened_shell_from_closing()

    def execute(self) -> None:
        try:
            self.args.target
        except AttributeError:
            parser.error("No command specified")
            sys.exit(2)

        try:
            self.__getattribute__(self.args.target)()
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
install_parser.set_defaults(target="install_plugin_symlink")

args = parser.parse_args()

installer_instance = Installer(args)
installer_instance.execute()
