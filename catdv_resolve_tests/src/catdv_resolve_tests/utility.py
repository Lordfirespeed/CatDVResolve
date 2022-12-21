from random import Random
import string
from enum import Enum


class ExtendedRandom(Random):
    class AsciiCharacters(Enum):
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        letters = string.ascii_letters
        digits = string.digits
        punctuation = string.punctuation
        alphanumeric = string.ascii_letters + string.digits
        everything = string.ascii_letters + string.digits + string.punctuation

    def ascii_string(self, length: int, string_type: AsciiCharacters = AsciiCharacters.letters) -> str:
        return "".join(self.choice(string_type.value) for _ in range(length))


class TestingHelper:
    __slots__ = ["random"]

    def __init__(self) -> None:
        self.random = ExtendedRandom()


Helper = TestingHelper()
