import logging
from typing import Optional
from pathlib import Path
import subprocess


class CommandOption:
    __slots__ = ["key"]

    def __init__(self, key: str) -> None:
        self.key = key

    def __str__(self) -> str:
        return f"--{self.key}"


class KeyValueCommandOption(CommandOption):
    __slots__ = ["value"]

    def __init__(self, key: str, value: str) -> None:
        super().__init__(key)
        self.value = value

    def __str__(self) -> str:
        return f"--{self.key}={self.value}"


class PathCommandOption(CommandOption):
    __slots__ = ["path"]

    def __init__(self, key: str, path: Path) -> None:
        super().__init__(key)
        self.path = path

    def __str__(self) -> str:
        return f"--{self.key}={str(self.path)}"


class SourceDestCommandOption(CommandOption):
    __slots__ = ["source_path", "destination_path"]

    def __init__(self, key: str, source: Path, destination: Path) -> None:
        super().__init__(key)
        self.source_path = source.resolve()
        self.destination_path = destination

    def __str__(self) -> str:
        return f"--{self.key}={str(self.source_path)}={str(self.destination_path)}"


class NuitkaBuildCommand:
    __slots__ = ["options", "target"]

    base_command = ("python", "-m", "nuitka")

    def __init__(self, target: Path, options: Optional[list[CommandOption]] = None) -> None:
        if options is None:
            options = []
        self.options: [CommandOption] = options
        self.target: Path = target.resolve()

    def add_option(self, option: CommandOption) -> None:
        self.options.append(option)

    def _add_source_dest(self, key: str, source: Path, destination: Path) -> None:
        self.add_option(SourceDestCommandOption(key, source, destination))

    def add_data_files(self, source: Path, destination: Path) -> None:
        self._add_source_dest("include-data-files", source, destination)

    def add_data_dir(self, source: Path, destination: Path) -> None:
        self._add_source_dest("include-data-dir", source, destination)

    def construct_args(self) -> [str]:
        return self.base_command + tuple(str(option) for option in self.options) + (self.target,)

    def construct_string(self) -> str:
        joined_options = " ".join(str(option) for option in self.options)
        return f"{self.base_command} {joined_options} {str(self.target)}"


def main_build():
    from os import chdir as oschdir
    oschdir(str(Path(__file__).parent.parent.resolve()))

    installer_command = NuitkaBuildCommand(Path(".", "installer", "catdv-resolve_installer.py"))

    installer_command.add_option(CommandOption("onefile"))
    installer_command.add_option(CommandOption("follow-imports"))
    installer_command.add_option(KeyValueCommandOption("enable-plugin", "pyside6"))
    installer_command.add_option(CommandOption("windows-uac-admin"))
    installer_command.add_option(PathCommandOption("onefile-tempdir-spec", Path("%TEMP%", "CatDVResolve_%PID%")))
    installer_command.add_data_files(Path(".", "install-requirements.txt"), Path("install-requirements.txt"))
    installer_command.add_data_files(Path(".", "install-requirements.bat"), Path("install-requirements.bat"))
    installer_command.add_data_dir(Path(".", "source"), Path("source"))
    installer_command.add_option(PathCommandOption("output-dir", Path(".", "build").resolve()))

    process = subprocess.Popen(installer_command.construct_args())
    try:
        assert process.wait(120) == 0
    except subprocess.TimeoutExpired:
        logging.critical("Compilation took an awfully long time, terminating process.")
        process.terminate()
    except AssertionError:
        logging.critical("Compilation returned a non-zero returncode, bad things could've happened.")


if __name__ == "__main__":
    main_build()
