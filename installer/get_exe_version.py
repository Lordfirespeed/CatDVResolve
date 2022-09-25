import pefile

filepath = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"


def get_file_info(pe: pefile.PE):
    if not hasattr(pe, 'VS_VERSIONINFO'):
        return

    for idx in range(len(pe.VS_VERSIONINFO)):
        if not (hasattr(pe, 'FileInfo') and len(pe.FileInfo) > idx):
            continue

        for entry in pe.FileInfo[idx]:
            if not hasattr(entry, 'StringTable'):
                continue

            for st_entry in entry.StringTable:
                for str_entry in sorted(list(st_entry.entries.items())):
                    print('{0}: {1}'.format(
                        str_entry[0].decode('utf-8', 'backslashreplace'),
                        str_entry[1].decode('utf-8', 'backslashreplace')))


def get_resolve_pe_version_data_encoded(pe: pefile.PE):
    if not hasattr(pe, 'VS_VERSIONINFO'):
        raise OSError
    if not hasattr(pe, 'FileInfo'):
        raise OSError
    if not len(pe.FileInfo) > 0:
        raise OSError
    if not len(pe.FileInfo[0]) > 0:
        raise OSError
    if not hasattr(pe.FileInfo[0][0], "StringTable"):
        raise OSError
    if not len(pe.FileInfo[0][0].StringTable) > 0:
        raise OSError
    return pe.FileInfo[0][0].StringTable[0].entries


def get_resolve_pe_version_data(pe: pefile.PE):
    encoded_version_data = get_resolve_pe_version_data_encoded(pe)
    return {key.decode("utf-8", "backslashreplace"): value.decode("utf-8", "backslashreplace") for key, value in encoded_version_data.items()}


def get_resolve_exe_version_data(filepath: str):
    pe = pefile.PE(filepath, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    return get_resolve_pe_version_data(pe)


def main():
    version_data = get_resolve_exe_version_data(filepath)
    if not version_data:
        return

    version = version_data["ProductVersion"]

    major_version_number = int(version[:version.index(".")])
    if major_version_number >= 18:
        download_url = "https://www.python.org/downloads/release/python-3107/"
    else:
        download_url = "https://www.python.org/downloads/release/python-368/"


if __name__ == "__main__":
    main()
