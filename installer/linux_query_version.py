import re
import subprocess
from pathlib import Path
from re import search, match

is_elf_pattern = re.compile(r"((?:\/\w+)+): (ELF)")
version_pattern = re.compile(r"(\d+)(?:\.\d+)*")


def get_resolve_executable_path_version(filepath: Path) -> str:
    if not filepath.exists():
        raise FileNotFoundError

    try:
        file_result = subprocess.run(("file", str(filepath)), capture_output=True)
        assert file_result.returncode == 0
    except FileNotFoundError as e:
        raise e
    except AssertionError:
        raise OSError

    file_result_output = file_result.stdout.decode("utf-8", "backslashreplace")
    file_is_elf_match = match(is_elf_pattern, file_result_output)
    if file_is_elf_match is None:
        raise OSError

    try:
        version_result = subprocess.run((filepath, "-v"), capture_output=True)
        assert version_result.returncode == 0
    except AssertionError:
        raise OSError

    version_output = version_result.stdout.decode("utf-8", "backslashreplace")

    if not version_output.startswith("DaVinci Resolve"):
        raise OSError

    version_text_match = search(version_pattern, version_output)
    if version_text_match is None:
        raise OSError

    return version_text_match.group()


if __name__ == "__main__":
    detected_version = get_resolve_executable_path_version(Path("opt", "resolve", "bin", "resolve"))
    print(detected_version)
