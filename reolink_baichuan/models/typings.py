""" Model Typings """

from enum import Enum, IntEnum
from typing import Union

class StreamType(Enum):
    """ Stream Types """

    MAIN = "main"
    SUB = "subStream"

class StreamId(IntEnum):
    """ Stream Ids """

    CLEAR = 0
    FLUENT = 1
    BALANCED = 4


BufferTypes = Union[bytearray, bytes, memoryview]

WriteBufferTypes = Union[bytearray, memoryview]
