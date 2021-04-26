""" Legacy Messages """

from dataclasses import dataclass, field
import struct

from typing import Optional, Tuple, Union, cast

from ..metadata import MSG_CLASS_LEGACY, Metadata, MetadataContext

from ..const import MSG_ID_LOGIN
from ..typings import BufferTypes, WriteBufferTypes

LOGIN_STRUCT = "32s32s"
LOGIN_STRUCT_SIZE = struct.calcsize(LOGIN_STRUCT)


@dataclass
class Login:
    """ Legacy Login """

    __msg_id__: int = field(
        default=MSG_ID_LOGIN, init=False, repr=False, hash=False, compare=False
    )
    __msg_class__: int = field(
        default=MSG_CLASS_LEGACY, init=False, repr=False, hash=False, compare=False
    )

    username: str
    password: str = None

    def __pack_to__(
        self, meta: Metadata, buffer: WriteBufferTypes, offset: int = 0
    ) -> Tuple[int, Optional[int]]:
        struct.pack_into(
            LOGIN_STRUCT,
            buffer,
            offset,
            self.username[:31],
            self.password[:31] if not self.password else "",
        )
        return (LOGIN_STRUCT_SIZE, None)

    @classmethod
    def __unpack_from__(
        cls, context: MetadataContext, buffer: BufferTypes, offset: int = 0
    ):
        _tuple = struct.unpack_from(LOGIN_STRUCT, buffer, offset)
        return (LOGIN_STRUCT_SIZE, cls(*_tuple))

class Unknown:
    """ Unknown Legacy Message """

    __msg_id__: int = field(
        default=0, init=False, repr=False, hash=False, compare=False
    )
    __msg_class__: int = field(
        default=0, init=False, repr=False, hash=False, compare=False
    )

    def __pack_into__(
        self, meta: Metadata, buffer: WriteBufferTypes, offset: int = 0
    ) -> Tuple[int, Optional[int]]:
        return (0, None)

    @classmethod
    def __unpack_from__(
        cls, context: MetadataContext, buffer: BufferTypes, offset: int = 0
    ):
        return (0, cast(cls, None))


Legacy = Union[Unknown, Login]


def unpack_from(meta: Metadata, buffer: BufferTypes, offset: int = 0) -> Legacy:
    if meta.msg_id == MSG_ID_LOGIN:
        return Login.__unpack_from__(buffer, offset)
    return Unknown.__unpack_from__(buffer, offset)