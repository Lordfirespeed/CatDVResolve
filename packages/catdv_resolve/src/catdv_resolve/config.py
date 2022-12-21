from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any


class _Config:
    __instance: _Config = None

    filepath = Path("config.json")
    _data: dict[str, Any]

    _defaults = {}

    def __init__(self):
        self._data = {}
        self.load_defaults()
        self.load_from_file()

    def __new__(cls, *args, **kwargs) -> _Config:
        if not cls.__instance:
            cls.__instance = super(_Config, cls).__new__(cls, *args, **kwargs)
        return cls.__instance

    def load_defaults(self):
        self._data |= self._defaults

    def load_from_file(self) -> None:
        if not self.filepath.is_file():
            logging.info("Couldn't find config file. Loading defaults.")
            self._data = self._defaults.copy()
            return

        with open(self.filepath) as config_file:
            new_data: dict = json.load(config_file)

        self._data |= new_data

    def dump_to_file(self) -> None:
        logging.info("Dumping config...")

        with open(self.filepath, "w") as config_file:
            json.dump(self._data, config_file, indent=4)

    def __getitem__(self, item: str) -> Any:
        return self._data[item]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.dump_to_file()


Config = _Config()
