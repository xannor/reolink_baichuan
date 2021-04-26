""" Modern Messages """

from dataclasses import dataclass
from typing import Optional
from ..metadata import (
    MSG_CLASS_MODERN,
    MSG_CLASS_MODERN_BINARY,
    Metadata,
    MetadataContext,
)
from ..const import MSG_ID_LOGIN, MSG_ID_SET_GENERAL
from ..typings import BufferTypes, WriteBufferTypes

from . import xml


@dataclass
class Modern:
    """ Modern Message """

    @property
    def __msg_id__(self) -> int:
        if isinstance(self.xml, xml.Body):
            if not self.xml.login_user is None:
                return MSG_ID_LOGIN
            if not self.xml.system_general is None:
                return MSG_ID_SET_GENERAL
        return 0

    @property
    def __msg_class__(self) -> int:
        if self.binary is None:
            return MSG_CLASS_MODERN
        return MSG_CLASS_MODERN_BINARY

    xml: xml.Xml = None
    binary: BufferTypes = None

    def __pack_into__(self, meta: Metadata, buffer: WriteBufferTypes, offset: int = 0):
        xml_buffer = buffer
        xml_offset = offset
        if meta.encrypted:
            xml_buffer = bytearray()
            xml_offset = 0
        wrote: int = (
            self.xml.__serialize_to__(xml_buffer, xml_offset)
            if not self.xml is None
            else 0
        )
        if meta.encrypted and wrote > 0:
            xml.crypto(xml_buffer, meta.client_idx.__to_int__())
            memoryview(buffer)[offset : offset + wrote] = xml_buffer
        offset += wrote
        bin_offset: Optional[int] = wrote
        if self.binary is None or self.__msg_class__ == MSG_CLASS_MODERN:
            bin_offset = None
        if not bin_offset is None:
            bin_len = len(self.binary)
            memoryview(buffer)[offset : offset + bin_len] = self.binary
            wrote += bin_len
        return (wrote, bin_offset)

    @classmethod
    def __unpack_from__(
        cls,
        context: MetadataContext,
        buffer: BufferTypes,
        offset: int = 0,
    ):
        xml_data = buffer
        xml_end = len(buffer)
        if not context.bin_offset is None:
            xml_end = context.bin_offset
        if context.metadata.encrypted:
            xml_data = xml.crypto(
                memoryview(xml_data)[:xml_end], context.metadata.client_idx.__to_int__()
            )
            xml_end = len(xml_data)
        xml_ = xml.parse(memoryview(xml_data)[:xml_end])

        binary = (
            memoryview(buffer)[offset + context.bin_offset :]
            if not context.bin_offset is None
            else None
        )

        return cls(xml_, binary)
