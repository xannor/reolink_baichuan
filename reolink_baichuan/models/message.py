""" Baichuan Protocol Message """

from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Union

from .const import (
    MSG_ID_GET_GENERAL,
    MSG_ID_PING,
    MSG_ID_VERSION,
    MSG_ID_VIDEO,
)

from .metadata import (
    HEADER_STRUCT_SIZE,
    MSG_CLASS_LEGACY,
    MSG_CLASS_MODERN,
    MSG_CLASS_MODERN_BINARY,
    MSG_CLASS_MODERN_OTHER,
    Metadata,
)

from .typings import BufferTypes, StreamType

from . import legacy
from .modern import Modern, xml

Body = Union[legacy.Legacy, Modern]


@dataclass
class Message:
    """ Message """

    meta: Metadata
    body: Body

    def tobytes(self):
        """ convert message to bytes """

        self.meta.msg_id = self.body.__msg_id__
        self.meta.msg_class = self.body.__msg_class__
        offset = HEADER_STRUCT_SIZE
        if (
            isinstance(self.body, Modern)
            and not self.body.binary is None
            and self.meta.msg_class in (MSG_CLASS_MODERN_BINARY, MSG_CLASS_MODERN_OTHER)
        ):
            offset += 4
        buffer = bytearray()
        (body_len, bin_offset) = self.body.__pack_into__(self.meta, buffer, offset)
        self.meta.__pack_into__(buffer, body_len, bin_offset)
        return bytes(buffer)

    @classmethod
    async def async_read(cls, read: Callable[[int], Awaitable[bytes]]):
        """ fetch bytes and convert to Message """

        context = await Metadata.async_read(read)
        data = await read(context.body_len)
        body: Body = None
        if _is_modern(context.metadata):
            body = Modern.__unpack_from__(context, data)
        else:
            body = legacy.unpack_from(context, data)

        return cls(context.metadata, body)

    @classmethod
    def from_legacy(cls, message: legacy.Legacy):
        """ Message from Legacy """

        meta = Metadata(message.__msg_id__, msg_class=message.__msg_class__)
        return cls(meta, message)

    @classmethod
    def from_xml(
        cls, xml_: xml.Xml, binary: Optional[BufferTypes] = None, encrypt: bool = True
    ):
        """ Modern Xml Message """

        body = Modern(xml_, binary)
        meta = Metadata(body.__msg_id__, body.__msg_class__, encrypted=encrypt)
        return cls(meta, body)

    @classmethod
    def login(cls, username: str, password: Optional[str] = None, encrypt: bool = True):
        """ Modern Login Message """

        return cls.from_xml(
            xml.Body(
                login_user=xml.LoginUser(username, password), login_net=xml.LoginNet()
            ),
            encrypt=encrypt,
        )

    @classmethod
    def ping(cls, encrypt: bool = True):
        """ Ping Message """

        return cls(Metadata(MSG_ID_PING, 0, MSG_CLASS_MODERN, encrypt), Modern())

    @classmethod
    def version(cls, encrypt: bool = True):
        """ Version Message """

        return cls(Metadata(MSG_ID_VERSION, 0, MSG_CLASS_MODERN, encrypt), Modern())

    @classmethod
    def preview(cls, channel_id: int = 0, stream_type: StreamType = StreamType.MAIN, encrypt: bool = True):
        """ Preview Message """

        preview = xml.Preview(channel_id, stream_type=stream_type)
        return cls(Metadata(MSG_ID_VIDEO, 0, MSG_CLASS_MODERN, encrypt), Modern(preview))

    @classmethod
    def general(cls, encrypt: bool = True):
        """ General Message """

        return cls(Metadata(MSG_ID_GET_GENERAL, 0, MSG_CLASS_MODERN, encrypt), Modern())


def _is_modern(self: Metadata):
    return self.msg_class != MSG_CLASS_LEGACY
