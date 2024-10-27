from enum import Enum


class SearchSort(Enum):
    GENERAL = "general"
    TIME = "time_descending"
    POPULAR = "popularity_descending"


class NoteType(Enum):
    GENERAL = 0
    VIDEO = 1
    IMAGE = 2
