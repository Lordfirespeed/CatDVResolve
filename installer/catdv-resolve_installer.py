from __future__ import annotations
from typing import Optional, Callable, ClassVar, Any, Protocol
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import subprocess
import logging
from shutil import copy, copytree, rmtree
from functools import cache
from PySide6.QtCore import Slot, Qt, QThread
from PySide6.QtWidgets import QWidget, QApplication, \
    QLabel, QWizard, QWizardPage, QFrame, QBoxLayout, \
    QGridLayout, QLineEdit, QFileDialog, QPushButton, QCheckBox


@dataclass
class PythonVersion:
    """Class for keeping track of a Resolve-compatible python version."""

    major: int
    minor: int
    patch: Optional[int] = None  # "None" represents any patch no. allowed

    compatibility: Callable[[int], bool] = field(default=lambda x: False, repr=False)
    download_url: str = ""

    releases_url: ClassVar[str] = "https://www.python.org/downloads/release/"

    def is_compatible_with(self, resolve_major_version: int) -> bool:
        return self.compatibility(resolve_major_version)

    def get_version_string(self):
        version_string = f"{self.major}.{self.minor}"
        if self.patch:
            version_string += f".{self.patch}"
        return version_string

    @classmethod
    def compatible_from_major_to_major(cls, from_version: int, to_version: int):
        def compatibility_function(resolve_major_version):
            return from_version <= resolve_major_version < to_version

        return compatibility_function


class ResolveCompatiblePythonVersions(Enum):
    ThreeTen = PythonVersion(3, 10, compatibility=PythonVersion.compatible_from_major_to_major(18, 20),
                             download_url=PythonVersion.download_url + "python-3107")
    ThreeSix = PythonVersion(3, 6, compatibility=PythonVersion.compatible_from_major_to_major(16, 18),
                             download_url=PythonVersion.download_url + "python-368")


class FileDialogGetCallable(Protocol):
    def __call__(self, parent: QWidget | QWidget | None, caption: str, dir: str,
                 options: Optional[QFileDialog.Options] = None) -> str:
        pass


class FileSelector(QFrame):
    def __init__(self, label_text: str, default_path: str,
                 mode: FileDialogGetCallable = QFileDialog.getOpenFileName) -> None:
        super().__init__()

        self.mode = mode

        self.layout = QGridLayout()

        self.layout.setColumnStretch(1, 0)
        self.layout.setColumnStretch(0, 1)

        self.label = QLabel(text=label_text)
        self.layout.addWidget(self.label, 0, 0)

        self.path_text_entry = QLineEdit(text=default_path)
        self.layout.addWidget(self.path_text_entry, 1, 0)

        self.button = QPushButton(text="...")
        self.layout.addWidget(self.button, 1, 1)

        self.setLayout(self.layout)

        self.button.pressed.connect(self.file_dialog)

    @Slot()
    def file_dialog(self) -> None:
        result = self.mode(self, caption=self.label.text(), dir=self.path_text_entry.text())
        if type(result) is tuple:
            filename = result[0]
        elif type(result) is str:
            filename = result
        elif type(result) is None or result == "":
            return
        else:
            raise TypeError

        filepath = Path(filename)

        self.path_text_entry.setText(str(filepath))

    def target_is_file(self) -> bool:
        path = Path(self.path_text_entry.text())
        return path.resolve().is_file()

    def target_is_dir(self) -> bool:
        path = Path(self.path_text_entry.text())
        return path.resolve().is_dir()


class CatDVInstaller:
    __slots__ = ["system_platform", "resolve_data_dir", "resolve_app_path", "resolve_version_data",
                 "python_executable_path_str", "install_target_path", "venv_path", "temp_path", "succeeded"]

    class Platform(Enum):
        Unknown = 0
        OSX = 1
        Linux = 2
        Windows = 3

        @classmethod
        def determine(cls) -> CatDVInstaller.Platform:
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

    def __init__(self):
        self.system_platform = self.Platform.determine()

        self.resolve_data_dir: Optional[Path] = None
        self.resolve_app_path: Optional[Path] = None
        self.resolve_version_data: Optional[dict[str, str]] = None
        self.python_executable_path_str: Optional[str] = None
        self.install_target_path: Optional[Path] = None
        self.venv_path: Optional[Path] = None
        self.temp_path: Optional[Path] = None
        self.succeeded: Optional[bool] = None

    def request_admin_escalation_or_exit(self):
        if self.system_platform != self.Platform.Windows:
            return

        from ctypes import windll
        if windll.shell32.IsUserAnAdmin():
            return

        if not sys.argv[0].endswith("exe"):
            success = windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1) > 32

        sys.exit()

    def get_linux_resolve_dir(self) -> Path:
        if self.system_platform != self.Platform.Linux:
            raise OSError

        opt_path = Path("/", "opt", "resolve").resolve()
        home_path = Path("/", "home", "resolve").resolve()

        if home_path.is_dir():
            return home_path
        else:
            return opt_path

    def get_filesystem_root(self) -> Path:
        if self.system_platform == self.Platform.OSX or self.system_platform == self.Platform.Linux:
            return Path("/").resolve()
        elif self.system_platform == self.Platform.Windows:
            return Path(r"C:\ ").resolve()
        else:
            raise NotImplementedError

    def get_default_resolve_app_path(self) -> Path:
        if self.system_platform == self.Platform.OSX:
            return Path("Applications", "DaVinci Resolve", "DaVinci Resolve.app")
        elif self.system_platform == self.Platform.Linux:
            return Path(self.get_linux_resolve_dir(), "bin", "resolve")
        elif self.system_platform == self.Platform.Windows:
            from os import getenv as osgetenv
            program_files = osgetenv("PROGRAMFILES")
            return Path(program_files, "Blackmagic Design", "DaVinci Resolve", "Resolve.exe")
        else:
            raise NotImplementedError

    def set_resolve_app_path(self, app_path: Path) -> None:
        if not isinstance(app_path, Path):
            return

        app_path = app_path.resolve()

        if not app_path.is_file():
            return

        try:
            self.resolve_version_data = self.get_resolve_executable_version_data(app_path)
        except OSError:
            return

        self.resolve_app_path = app_path

    def get_resolve_system_scripts_directory(self) -> Path:
        if self.system_platform == self.Platform.OSX:
            return Path("Library", "Application Support", "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts")
        elif self.system_platform == self.Platform.Linux:
            return Path(self.get_linux_resolve_dir(), "Fusion", "Scripts")
        elif self.system_platform == self.Platform.Windows:
            from os import getenv as osgetenv
            return Path(osgetenv("PROGRAMDATA"), "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts")
        else:
            raise NotImplementedError

    def get_resolve_user_scripts_directory(self) -> Path:
        if self.system_platform == self.Platform.OSX:
            from os import getlogin as osgetlogin
            return Path("Users", osgetlogin(), "Library", "Application Support", "Blackmagic Design", "DaVinci Resolve",
                        "Fusion", "Scripts")
        elif self.system_platform == self.Platform.Linux:
            from os import getenv as osgetenv
            return Path(osgetenv("HOME"), ".local", "share", "DaVinciResolve", "Fusion", "Scripts")
        elif self.system_platform == self.Platform.Windows:
            from os import getenv as osgetenv
            return Path(osgetenv("APPDATA"), "Roaming", "Blackmagic Design", "DaVinci Resolve", "Support", "Fusion",
                        "Scripts")
        else:
            raise NotImplementedError

    def get_resolve_executable_version_data(self, app_path: Path) -> dict[str, str]:
        if self.system_platform == self.Platform.OSX:
            return {}
        elif self.system_platform == self.Platform.Linux:
            from linux_query_version import get_resolve_executable_path_version
            return {"ProductVersion": get_resolve_executable_path_version(app_path)}
        elif self.system_platform == self.Platform.Windows:
            from get_exe_version import get_resolve_exe_version_data
            return get_resolve_exe_version_data(str(app_path))
        else:
            raise NotImplementedError

    @staticmethod
    def strip_encoded_stdout_lines(stdout_str: bytes) -> [str]:
        return [line.strip() for line in stdout_str.decode("utf-8", "backslashreplace").strip().split("\n")]

    def get_python_executable_path_strs(self) -> [str]:
        if self.system_platform == self.Platform.OSX:
            return []
        elif self.system_platform == self.Platform.Linux:
            try:
                find_result = subprocess.run(
                    ("usr/bin/find", "/usr/bin", "/usr/local/bin", "-name", "python*", "!", "-type", "l"),
                    capture_output=True)
                assert find_result.returncode == 0
            except FileNotFoundError as e:
                print("Couldn't find the find command. Install it to /usr/bin/find")
                raise e
            except AssertionError:
                return []

            return self.strip_encoded_stdout_lines(find_result.stdout)
        elif self.system_platform == self.Platform.Windows:
            try:
                where_result = subprocess.run(("where", "python"), capture_output=True)
                assert where_result.returncode == 0
            except AssertionError:
                return []

            return self.strip_encoded_stdout_lines(where_result.stdout)
        else:
            raise NotImplementedError

    def determine_required_python_version(self) -> PythonVersion:
        if self.resolve_version_data is None:
            raise AttributeError

        try:
            version_string = self.resolve_version_data["ProductVersion"]
            major_version_number = int(version_string[:version_string.index(".")])

            for python_version in ResolveCompatiblePythonVersions:
                if python_version.value.is_compatible_with(major_version_number):
                    return python_version.value

            raise NotImplementedError  # as the installed Resolve version is not a known one, it is incompatible

        except (KeyError, ValueError):
            raise AttributeError

    def get_python_executable_path_str_of_version(self, version: PythonVersion) -> str:
        encoded_version = f"{version.major}.{version.minor}".encode("utf-8")
        for python_exe_path in self.get_python_executable_path_strs():
            try:
                python_version_result = subprocess.run((python_exe_path, "-c", "import sys; print(sys.version)"),
                                                       capture_output=True)
            except FileNotFoundError:
                continue
            if python_version_result.returncode != 0:
                continue

            if python_version_result.stdout.startswith(encoded_version):
                return python_exe_path

        raise OSError

    def get_required_python_executable_path_str(self):
        required_version = self.determine_required_python_version()
        return self.get_python_executable_path_str_of_version(required_version)

    def discover_required_python_executable_path_str(self) -> None:
        try:
            required_version_path_str = self.get_required_python_executable_path_str()
            assert required_version_path_str is not None
        except (OSError, AssertionError) as e:
            logging.exception(e)
            return

        self.python_executable_path_str = required_version_path_str

    def get_default_install_target_systemwide(self) -> Path:
        if self.system_platform == self.Platform.OSX:
            return Path("Library", "Application Support", "Square Box", "CatDV-Resolve")
        elif self.system_platform == self.Platform.Linux:
            return Path("/", "opt", "catdv-resolve")
        elif self.system_platform == self.Platform.Windows:
            from os import getenv as osgetenv
            return Path(osgetenv("PROGRAMFILES"), "Square Box", "CatDV-Resolve")
        else:
            raise NotImplementedError

    def set_install_target(self, install_target_path: str) -> None:
        self.install_target_path = Path(install_target_path)

    @cache
    def get_packaged_files_location(self) -> Path:
        if sys.argv[0].endswith("py"):
            return Path(__file__).resolve().parent.parent
        if self.system_platform == self.Platform.OSX:
            raise NotImplementedError
        elif self.system_platform == self.Platform.Linux:
            raise NotImplementedError
        elif self.system_platform == self.Platform.Windows:
            from os import getenv as osgetenv, getpid as osgetpid, getppid as osgetppid
            return Path(osgetenv("TEMP"), f"CatDVResolve_{osgetppid()}")
        else:
            raise NotImplementedError

    def create_venv(self) -> None:
        if self.venv_path is None:
            raise AttributeError

        try:
            create_venv_result = subprocess.run((self.python_executable_path_str, "-m", "venv", str(self.venv_path)), capture_output=True)
            assert create_venv_result.returncode == 0
        except AssertionError:
            raise OSError

    def install_dependencies_to_venv(self) -> None:
        if self.venv_path is None or self.temp_path is None:
            raise AttributeError

        copy_from = self.get_packaged_files_location()
        copy(Path(copy_from, "install-requirements.txt"), self.temp_path)

        if self.system_platform == self.Platform.Linux or self.system_platform == self.Platform.OSX:
            try:
                result = subprocess.run(f"cd {str(self.install_target_path)} && source ./venv/bin/activate && pip install -r ./temp/install-requirements.txt", shell=True)
                assert result.returncode == 0
            except AssertionError:
                raise OSError
        elif self.system_platform == self.Platform.Windows:
            copy(Path(copy_from, "install-requirements.bat"), self.temp_path)
            try:
                result = subprocess.run((str(Path(self.temp_path, "install-requirements.bat")), str(self.install_target_path)))
                assert result.returncode == 0
            except AssertionError:
                raise OSError
        else:
            raise NotImplementedError

    def copy_source(self) -> None:
        if self.install_target_path is None:
            raise AttributeError

        copy_from = self.get_packaged_files_location()
        copytree(Path(copy_from, "source"), Path(self.install_target_path, "source"))

    def create_bootstrap_symlink(self):
        if self.install_target_path is None:
            raise AttributeError

        from os import symlink as ossymlink

        symlink_destination = Path(self.get_resolve_system_scripts_directory(), "Utility", "CatDV-Resolve.py")
        symlink_destination.unlink(missing_ok=True)

        ossymlink(Path(self.install_target_path, "source", "bootstrap.py"), symlink_destination)

    def execute(self):
        try:
            self._execute()
        except Exception as e:
            self.succeeded = False
            logging.exception(e)
            return

        self.succeeded = True

    def _execute(self):
        self.install_target_path.mkdir(parents=True, exist_ok=False)  # raises FileExistsError
        self.venv_path = Path(self.install_target_path, "venv")
        self.temp_path = Path(self.install_target_path, "Temp")
        self.create_venv()
        self.temp_path.mkdir(exist_ok=True)
        self.install_dependencies_to_venv()
        self.copy_source()
        rmtree(self.temp_path)
        self.create_bootstrap_symlink()


class CatDVWizardPage(QWizardPage):
    page_id = 99999
    subtitle = "Subtitle"
    back_button_disabled = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.back_button_disabled:
            self.setCommitPage(True)

        self.setTitle(self.subtitle)

    def wizard(self) -> CatDVWizard:
        wizard = super(CatDVWizardPage, self).wizard()
        if not (wizard is None or isinstance(wizard, CatDVWizard)):
            raise TypeError
        return wizard


class PageWithText(CatDVWizardPage):
    content = "Placeholder"
    open_external_links = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        page_layout = QBoxLayout(QBoxLayout.TopToBottom)
        self.setLayout(page_layout)

        self.content_label = QLabel()
        self.content_label.setWordWrap(True)
        self.content_label.setOpenExternalLinks(self.open_external_links)
        self.content_label.setTextFormat(Qt.RichText)
        self.content_label.setText(self.content)

        self.layout().addWidget(self.content_label)


class CatDVWizard(QWizard):
    installer = CatDVInstaller()

    def __init__(self, *args, **kwargs):
        super(CatDVWizard, self).__init__(*args, **kwargs)

        self.installer.request_admin_escalation_or_exit()

        self.setOption(self.IndependentPages, False)
        self.setWindowTitle("Install CatDV-Resolve")
        self.setButtonText(self.CommitButton, self.button(self.NextButton).text())

        for page in self.pages:
            self.setPage(page.page_id, page())

        self.setStartId(0)

        self.show()

    class IntroductionPage(PageWithText):
        page_id = 0
        subtitle = "Introduction"
        content = "This wizard will help you to install the CatDV-Resolve panel client."

        def nextId(self) -> int:
            return 1

    class LookForResolvePage(CatDVWizardPage):
        page_id = 1

        def initializePage(self) -> None:
            super().initializePage()
            self.wizard().installer.set_resolve_app_path(self.get_resolve_path())
            self.wizard().next()

        def nextId(self) -> int:
            if self.wizard().installer.resolve_app_path is not None:
                return CatDVWizard.LookForPythonPage.page_id
            else:
                return CatDVWizard.AskAboutResolvePage.page_id

        def check_entered_path(self):
            entered_path_string = self.field("ExecutablePath")
            entered_path_path = Path(entered_path_string)
            if not entered_path_path.is_file():
                raise OSError
            return entered_path_path

        def check_default_path(self):
            default_path = self.wizard().installer.get_default_resolve_app_path()
            if not default_path.is_file():
                raise OSError
            return default_path

        def get_resolve_path(self):
            try:
                return self.check_default_path()
            except OSError:
                pass

            try:
                return self.check_entered_path()
            except OSError:
                pass

    class LookForResolveAgainPage(LookForResolvePage):
        page_id = 6

        def nextId(self) -> int:
            if self.wizard().installer.resolve_app_path is not None:
                return CatDVWizard.LookForPythonPage.page_id
            else:
                return CatDVWizard.RestartPage.page_id

    class AskAboutResolvePage(PageWithText):
        page_id = 100
        subtitle = "DaVinci Resolve"
        content = "Your DaVinci Resolve installation could not be found. Is DaVinci Resolve installed?"

        def __init__(self):
            super().__init__()

            checkbox = QCheckBox()
            checkbox.setText("Yes, Resolve is installed")
            checkbox.setChecked(False)

            self.layout().addWidget(checkbox)
            self.registerField("UserSaysResolveIsInstalled", checkbox)

        def nextId(self) -> int:
            if self.field("UserSaysResolveIsInstalled") is True:
                return CatDVWizard.SelectResolveExecutablePage.page_id
            else:
                return CatDVWizard.DownloadResolvePage.page_id

    class SelectResolveExecutablePage(PageWithText):
        page_id = 110
        subtitle = "DaVinci Resolve"
        content = "Select your DaVinci Resolve app executable."

        def __init__(self):
            super().__init__()

            self.resolve_file_selector = FileSelector("Executable Path:",
                                                      str(CatDVWizard.installer.get_filesystem_root()))
            self.registerField("ExecutablePath", self.resolve_file_selector.path_text_entry)

            self.resolve_file_selector.path_text_entry.textChanged.connect(self.emit_complete_changed)

            self.layout().addWidget(self.resolve_file_selector)

        def isComplete(self) -> bool:
            return self.resolve_file_selector.target_is_file()

        @Slot()
        def emit_complete_changed(self):
            self.completeChanged.emit()

        def nextId(self) -> int:
            return CatDVWizard.LookForResolveAgainPage.page_id

    class DownloadResolvePage(PageWithText):
        page_id = 120
        subtitle = "DaVinci Resolve"
        content = "You can download DaVinci Resolve <a href=\"https://www.blackmagicdesign.com/products/davinciresolve/\">from Blackmagic Design's website<a>."

        def nextId(self) -> int:
            return CatDVWizard.LookForResolveAgainPage.page_id

    class LookForPythonPage(CatDVWizardPage):
        page_id = 2

        def __init__(self):
            super().__init__()
            self.python_path: Optional[Path] = None

        def initializePage(self) -> None:
            self.wizard().installer.discover_required_python_executable_path_str()
            self.wizard().next()

        def nextId(self) -> int:
            if self.wizard().installer.python_executable_path_str is not None:
                return CatDVWizard.CommitToInstallPage.page_id
            else:
                return CatDVWizard.DownloadPythonPage.page_id

    class LookForPythonAgainPage(LookForPythonPage):
        page_id = 7

        def nextId(self) -> int:
            if self.wizard().installer.python_executable_path_str is not None:
                return CatDVWizard.CommitToInstallPage.page_id
            else:
                return CatDVWizard.RestartPage.page_id

    class DownloadPythonPage(PageWithText):
        page_id = 200
        subtitle = "Python Couldn't be Found"
        content = "Your Python installation could not be found. Download python from BLAH"

        def nextId(self) -> int:
            return CatDVWizard.LookForPythonAgainPage.page_id

    class CommitToInstallPage(PageWithText):
        page_id = 3
        subtitle = "Install"
        content = "You are about to install the CatDV-Resolve panel client."

        def __init__(self):
            super().__init__()
            self.target_file_selector = FileSelector("Install Target:",
                                                     str(CatDVWizard.installer.get_default_install_target_systemwide()),
                                                     mode=QFileDialog.getExistingDirectory)

            self.registerField("InstallTargetDirectory", self.target_file_selector.path_text_entry)

            self.layout().addWidget(self.target_file_selector)

        def nextId(self) -> int:
            return CatDVWizard.ConsoleDuringInstallPage.page_id

    class InstallThread(QThread):
        def __init__(self, wizard: CatDVWizard, parent=None) -> None:
            super().__init__(parent)
            self.wizard = wizard

        def run(self):
            self.wizard.installer.execute()

    class ConsoleDuringInstallPage(CatDVWizardPage):
        page_id = 4

        def __init__(self):
            super().__init__()
            self.thread: Optional[QThread] = None

        def initializePage(self) -> None:
            self.wizard().installer.set_install_target(self.field("InstallTargetDirectory"))

            self.thread = CatDVWizard.InstallThread(self.wizard())
            self.thread.finished.connect(self.go_next)
            self.thread.start()

        @Slot()
        def go_next(self):
            self.wizard().next()

        def isComplete(self) -> bool:
            return False

        def nextId(self) -> int:
            if self.wizard().installer.succeeded:
                return CatDVWizard.ConclusionPage.page_id
            else:
                return CatDVWizard.FailedPage.page_id

    class ConclusionPage(PageWithText):
        page_id = 5
        subtitle = "Conclusion"
        content = "The CatDV-Resolve panel client has been successfully installed."

        def nextId(self) -> int:
            return -1

    class FailedPage(PageWithText):
        page_id = 8
        subtitle = "Failure"
        content = "The CatDV-Resolve panel client could not be installed."

        def nextId(self) -> int:
            return -1

    class RestartPage(CatDVWizardPage):
        page_id = 10

        def initializePage(self) -> None:
            self.wizard().restart()

    pages = {
        IntroductionPage,
        LookForResolvePage,
        AskAboutResolvePage,
        SelectResolveExecutablePage,
        DownloadResolvePage,
        LookForResolveAgainPage,
        LookForPythonPage,
        DownloadPythonPage,
        CommitToInstallPage,
        ConsoleDuringInstallPage,
        ConclusionPage,
        FailedPage,
        RestartPage
    }


if __name__ == "__main__":
    app = QApplication(sys.argv)

    wizard = CatDVWizard()

    sys.exit(app.exec())
