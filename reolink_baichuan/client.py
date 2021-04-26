"""
client
"""

import logging
import hashlib
import asyncio

from .const import DEFAULT_TIMEOUT
from .typings import Connection

from . import models

_LOGGER = logging.getLogger(__name__)

class Client:
    """ Baichuan Client """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout: int = DEFAULT_TIMEOUT
    ):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._timeout = timeout
        self._connection: Connection = None
        self._ready = False

    @property
    def connected(self):
        """ Return the client connection status """
        return self._connection is not None

    @property
    def authenticated(self):
        """ Return the client authnetication status """
        return self._ready
    
    async def _ensure_connection(self):
        if not self._connection:
            connect = asyncio.open_connection(self._host, self._port)
            try:
                self._connection = await asyncio.wait_for(connect, timeout=self._timeout)
            except asyncio.TimeoutError:
                _LOGGER.warn("Connection to %s timed out", self._host)
                self._connection = None
                self._ready = False
                return False
        
        if self._connection.writer.transport.is_closing():
            self._ready = False
            return False

        return True

    async def _send(self, message: models.Message, drain: bool = True):
        await self._ensure_connection()
        self._connection.writer.write(message.tobytes())
        if drain:
            await self._connection.writer.drain()

    async def _recv(self, exact: bool = True):
        if exact:
            read = models.Message.async_read(self._connection.reader.readexactly)
        else:
            read = models.Message.async_read(self._connection.reader.read)

        try:
            return await asyncio.wait_for(read, timeout=self._timeout)
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for response from %s", self._host)

    async def _ensure_auth(self):
        if self._ready:
            return True

        _LOGGER.debug(
            "Reolink camera with host %s:%s trying to log in with user %s",
            self._host,
            self._port,
            self._username
        )

        md5_username = _md5_string(self._username)
        md5_password = _md5_string(self._password)

        legacy_login = models.Message.from_legacy(
            models.LegacyLogin(md5_username, md5_password)
        )
        await self._send(legacy_login)
        login_reply = await self._recv()
        xml: models.XmlBody = login_reply.body.xml
        nonce = xml.encryption.nonce

        md5_username = _md5_string(f"{self._username}{nonce}", False)
        md5_password = _md5_string(f"{self._password}{nonce}", False)

        modern_login = models.Message.login(md5_username, md5_password)
        await self._send(modern_login)
        modern_reply = await self._recv()
        xml = modern_reply.body.xml

        return True

    async def ping(self):
        """ Ping (NoOp) camera """

        if not await self._ensure_auth():
            return False
        ping = models.Message.ping()
        await self._send(ping)
        #ping_reply = 
        await self._recv()
        # xml: models.XmlBody = ping_reply.body.xml
        return True

    async def get_version(self):
        """ Get Camera Version Info """

        if not await self._ensure_auth():
            return None
        version = models.Message.version()
        await self._send(version)
        version_reply = await self._recv()
        xml: models.XmlBody = version_reply.body.xml

        return xml.version_info

    async def get_general(self):
        """ Get Camera General Info """

        if not await self._ensure_auth():
            return None

        general = models.Message.general()
        await self._send(general)
        general_reply = await self._recv()
        xml: models.XmlBody = general_reply.body.xml

        return xml.system_general

    async def get_stream(self):
        """ Get Camera Stream """

        if not await self._ensure_auth():
            return None

        preview = models.Message.preview()
        await self._send(preview)
        # TODO : the rest


    async def close(self):
        """ Close camera connection """

        if not self.connected:
            return False
        
        connection = self._connection
        self._connection = None
        self._ready = False
        connection.writer.close()
        await connection.writer.wait_closed()

        return True
        
def _md5_string(input: str, padzero: bool = True):
    if len(input) > 0:
        input = hashlib.md5(input).hexdigest()

    if padzero:
        return input.ljust(32, "\0")
    