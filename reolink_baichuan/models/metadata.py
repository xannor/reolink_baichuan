""" Protocol Metadata """

import struct

from dataclasses import dataclass, field
from typing import Awaitable, Callable, NamedTuple, Optional

from .typings import StreamType, BufferTypes, WriteBufferTypes

MSG_CLASS_LEGACY = 0x6514
MSG_CLASS_MODERN = 0x6614
MSG_CLASS_MODERN_BINARY = 0x6414
MSG_CLASS_MODERN_OTHER = 0x0000

MAGIC_HEADER = 0xABCDEF0
HEADER_STRUCT = "!IIIIBBH"
HEADER_STRUCT_SIZE = struct.calcsize(HEADER_STRUCT)


def has_bin_offset(msg_class: int):
    """ determine if class should have binday data """
    return msg_class == 0x6414 or msg_class == 0x000


CLIENT_ID_STRUCT = "BBBB"
CLIENT_ID_STRUCT_SIZE = struct.calcsize(CLIENT_ID_STRUCT)


class _ClientIndex(NamedTuple):
    """ Client Index """

    channel_id: int
    stream: int
    unused: int
    handle: int


@dataclass
class ClientIndex:
    """ Client Identifier """

    channel_id: int = 0
    stream: StreamType = StreamType.BALANCED
    handle: int = 0

    def __pack_into__(self, buffer: WriteBufferTypes, offset: int = 0):
        _tuple = _ClientIndex(self.channel_id, self.stream, 0, self.handle)
        struct.pack_into(CLIENT_ID_STRUCT, buffer, offset, *_tuple)
        return CLIENT_ID_STRUCT_SIZE

    def __to_int__(self):
        buffer = bytearray(CLIENT_ID_STRUCT_SIZE)
        self.__pack_into__(buffer)
        return int.from_bytes(buffer)

    @classmethod
    def __unpack_from__(cls, buffer: BufferTypes, offset: int = 0):
        _tuple = _ClientIndex(*struct.unpack_from(CLIENT_ID_STRUCT, buffer, offset))
        return (
            CLIENT_ID_STRUCT_SIZE,
            cls(_tuple.channel_id, _tuple.stream, _tuple.handle),
        )

    @classmethod
    def __from_int__(cls, value: int):
        buffer = value.to_bytes(CLIENT_ID_STRUCT_SIZE)
        (_, self) = cls.__unpack_from__(buffer, 0)
        return self


class _Header(NamedTuple):
    """ Header """

    magic: int
    msg_id: int
    body_len: int
    enc_offset: int
    encrypted: int
    unknown: int
    msg_class: int


@dataclass
class Metadata:
    """ Metadata """

    msg_id: int = 0
    client_idx: ClientIndex = field(default_factory=ClientIndex)
    msg_class: int = 0
    encrypted: bool = False

    def __pack_into__(
        self,
        buffer: WriteBufferTypes,
        body_len: int,
        bin_offset: Optional[int] = None,
        offset: int = 0,
    ):
        _tuple = _Header(
            MAGIC_HEADER,
            self.msg_id,
            body_len,
            self.client_idx.__to_int__(),
            self.encrypted,
            0,
            self.msg_class,
        )

        struct.pack_into(HEADER_STRUCT, buffer, offset, *_tuple)
        size = HEADER_STRUCT_SIZE
        offset += HEADER_STRUCT_SIZE
        if not bin_offset is None:
            size += 4
            memoryview(buffer)[offset : offset + 4] = bin_offset.to_bytes(4)

        return size

    @classmethod
    def __unpack_from__(cls, buffer: BufferTypes, offset: int = 0):
        _tuple = _Header(*struct.unpack_from(HEADER_STRUCT, buffer, offset))
        size = HEADER_STRUCT_SIZE
        offset += size
        bin_offset: Optional[int] = None
        if _Header.msg_class in (MSG_CLASS_MODERN_BINARY, MSG_CLASS_MODERN_OTHER):
            if size + 4 < len(buffer):
                bin_offset = int.from_bytes(memoryview(buffer)[offset:4])
                size += 4
            else:
                bin_offset = -1

        return (
            size,
            cls(
                _tuple.msg_id,
                ClientIndex.__from_int__(_tuple.enc_offset),
                _tuple.msg_class,
                _tuple.encrypted,
            ),
            _tuple.body_len,
            bin_offset,
        )

    @classmethod
    async def async_read(cls, read: Callable[[int], Awaitable[bytes]]):
        """ read bytes and convert to Metadata """
        data = await read(HEADER_STRUCT_SIZE)
        (size, meta, body_len, bin_offset) = cls.__unpack_from__(data)
        if bin_offset == -1:
            bin_offset = int.from_bytes(await read(4))
            size += 4
        return MetadataContext(meta, body_len, bin_offset)


class MetadataContext(NamedTuple):
    """ Header Context """

    metadata: Metadata
    body_len: int
    bin_offset: Optional[int]
