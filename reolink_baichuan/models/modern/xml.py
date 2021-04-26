""" Xml Models """

from dataclasses import dataclass, fields
from typing import (
    ClassVar,
    Dict,
    Iterable,
    Optional,
    TypeVar,
    Union,
    cast,
    get_args,
    get_type_hints,
)

import xml.etree.ElementTree as etree

from ..typings import BufferTypes, StreamType

VERSION = "1.1"


@dataclass
class Encryption:
    """ Encryption """

    _attributes: ClassVar[Dict[str, str]] = {"version": "version"}
    _elements: ClassVar[Dict[str, str]] = {"type_": "type"}

    type_: str
    nonce: str
    version: str = VERSION


@dataclass
class LoginUser:
    """ Login User """

    _attributes: ClassVar[Dict[str, str]] = {
        "version": "version",
    }
    _elements: ClassVar[Dict[str, str]] = {
        "username": "userName",
        "user_ver": "userVer",
    }

    username: str
    password: str = None
    user_ver: int = 1
    version: str = VERSION


@dataclass
class LoginNet:
    """ Login Net """

    _attributes: ClassVar[Dict[str, str]] = {
        "version": "version",
    }
    _elements: ClassVar[Dict[str, str]] = {
        "type_": "type",
        "udp_port": "udpPort",
    }

    type_: str = "LAN"
    udp_port: int = 0
    version: str = VERSION


@dataclass
class Resolution:
    """ Resolution """

    _elements: ClassVar[Dict[str, str]] = {
        "name": "resolutionName",
    }

    name: str
    width: int
    height: int


@dataclass
class DeviceInfo:
    """ Device Info """

    resolution: Resolution


@dataclass
class VersionInfo:
    """ Version Info """

    _elements: ClassVar[Dict[str, str]] = {
        "serial_number": "serialNumber",
        "build_day": "buildDay",
        "hardware_version": "hardwareVersion",
        "config_version": "cfgVersion",
        "firmware_version": "firmwareVersion",
    }

    name: str
    serial_number: str
    build_day: str
    hardware_version: str
    config_version: str
    firmware_version: str
    detail: str


@dataclass
class Preview:
    """ Preview """

    _attributes: ClassVar[Dict[str, str]] = {
        "version": "version",
    }
    _elements: ClassVar[Dict[str, str]] = {
        "channel_id": "channelId",
        "stream_type": "streamType",
    }

    channel_id: int
    handle: int = 0
    stream_type: StreamType = StreamType.MAIN
    version: str = VERSION


@dataclass
class SystemGeneral:
    """ System General """

    _attributes: ClassVar[Dict[str, str]] = {
        "version": "version",
    }
    _elements: ClassVar[Dict[str, str]] = {
        "timezone": "timeZone",
        "osd_format": "osdFormat",
        "time_format": "timeFormat",
        "device_name": "deviceName",
    }

    timezone: int = None
    year: int = None
    month: int = None
    day: int = None
    hour: int = None
    minute: int = None
    second: int = None
    osd_format: str = None
    time_format: int = None
    language: str = None
    device_name: str = None
    version: str = VERSION


@dataclass
class Norm:
    """ Norm """

    _attributes: ClassVar[Dict[str, str]] = {
        "version": "version",
    }

    norm: str
    version: str = VERSION


@dataclass
class Body:
    """ Xml Body """

    _root: ClassVar[str] = "body"

    _elements: ClassVar[Dict[str, str]] = {
        "encryption": "Encryption",
        "login_user": "LoginUser",
        "login_net": "LoginNet",
        "device_info": "DeviceInfo",
        "version_info": "VersionInfo",
        "preview": "Preview",
        "system_general": "SystemGeneral",
        "norm": "Norm",
    }

    encryption: Encryption = None
    login_user: LoginUser = None
    login_net: LoginNet = None
    device_info: DeviceInfo = None
    version_info: VersionInfo = None
    preview: Preview = None
    system_general: SystemGeneral = None
    norm: Norm = None


@dataclass
class Extension:
    """ Xml Extension """

    _elements: ClassVar[Dict[str, str]] = {
        "binary": "binaryData",
    }

    binary: BufferTypes


XML_KEY = bytes(0x1F, 0x2D, 0x3C, 0x4B, 0x5A, 0x69, 0x78, 0xFF)

T = TypeVar("T")

Xml = Union[Body, Extension]

_roots: Dict[str, type] = {}
for t in get_args(Xml):
    t2 = cast(type, t)
    n = getattr(t2, "_root", t2.__name__)
    _roots[n] = t2

TO_STR = (int, bool, float, str)


def _from_xml(self: etree.Element, type_: type):
    attrs: Dict[str, str] = getattr(type_, "_attributes", None)
    elems: Dict[str, str] = getattr(type_, "_elements", None)

    _fields = {}
    for field in fields(type_):
        attr_value = None
        if not attrs is None and field.name in attrs:
            attr_value = self.get(attrs.get(field.name), None)
        elif not elems is None and field.name in elems:
            attr_value = self.find(elems.get(field.name))
        else:
            attr_value = self.find(field.name)

        if not attr_value is None:
            if field.type in TO_STR and etree.iselement(attr_value):
                attr_value = field.type(attr_value.text)
            elif etree.iselement(attr_value):
                attr_value = _from_xml(attr_value, field.type)

        if attr_value is None:
            _fields[field.name] = (
                field.default_factory()
                if not field.default_factory is None
                else field.default
            )
        else:
            _fields[field.name] = attr_value

    return type_(None, **_fields)


def parse(buffer: BufferTypes):
    """ Parse Xml From Buffer """

    root = etree.fromstring(buffer.tobytes().decode("utf-8"))

    type_ = _roots[root.tag]
    return cast(Xml, _from_xml(root, type_))


def _to_xml(self: etree.Element, value, type_: Optional[type] = None):
    if type_ is None:
        type_ = type(value)

    attrs: Dict[str, str] = getattr(type_, "_attributes", None)
    elems: Dict[str, str] = getattr(type_, "_elements", None)

    for field in fields(type_):
        attr_value = getattr(value, field.name, None)
        if attr_value is None:
            continue

        if (
            not attrs is None
            and field.name in attrs  # pylint: disable=unsupported-membership-test
        ):
            self.set(attrs.get(field.name), str(getattr(value, field.name, "")))
            continue

        child = etree.SubElement(
            self,
            elems.get(field.name)
            if not elems is None
            and field.name in elems  # pylint: disable=unsupported-membership-test
            else field.name,
        )
        if field.type in TO_STR:
            child.text = str(attr_value)
            continue

        _to_xml(child, attr_value, field.type)

    return self


def serialize(xml: Xml) -> bytes:
    """ serialize Xml to buffer """

    type_: type = type(xml)
    tag = getattr(type_, "_root", type_.__name__)
    root = etree.Element(tag)

    _to_xml(root, xml, type_)

    return etree.tostring(root, encoding="utf-8", xml_declaration=True)


def _cycle(itr: Iterable[T]):
    while True:
        for i in itr:
            yield i


def _skip(itr: Iterable[T], length: int):
    idx = 0
    for i in itr:
        idx += 1
        if idx < length:
            continue
        yield i


def crypto(buffer: BufferTypes, enc_offset: int = 0):
    """ Encrypt/Decrypt """

    return bytes(
        k ^ b ^ enc_offset for k, b in zip(_skip(_cycle(XML_KEY), enc_offset), buffer)
    )
