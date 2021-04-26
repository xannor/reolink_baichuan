"""
Common Typed Definitions
"""

from asyncio import StreamReader, StreamWriter

from typing import NamedTuple


class Connection(NamedTuple):
    """
    Connection Container
    """
    reader: StreamReader
    writer: StreamWriter
    