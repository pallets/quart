from __future__ import annotations

import io
from cgi import parse_header
from shutil import copyfileobj
from typing import Any, BinaryIO, Dict, Iterable, Optional


class FileStorage:
    """A thin wrapper over incoming files."""

    def __init__(
        self,
        stream: BinaryIO = None,
        filename: str = None,
        name: str = None,
        content_type: str = None,
        headers: Dict = None,
    ) -> None:
        self.name = name
        self.stream = stream or io.BytesIO()
        self.filename = filename
        if headers is None:
            headers = {}
        self.headers = headers
        if content_type is not None:
            headers["Content-Type"] = content_type

    @property
    def content_type(self) -> Optional[str]:
        """The content-type sent in the header."""
        return self.headers.get("Content-Type")

    @property
    def content_length(self) -> int:
        """The content-length sent in the header."""
        return int(self.headers.get("content-length", 0))

    @property
    def mimetype(self) -> str:
        """Returns the mimetype parsed from the Content-Type header."""
        return parse_header(self.headers.get("Content-Type"))[0]

    @property
    def mimetype_params(self) -> Dict[str, str]:
        """Returns the params parsed from the Content-Type header."""
        return parse_header(self.headers.get("Content-Type"))[1]

    def save(self, destination: BinaryIO, buffer_size: int = 16384) -> None:
        """Save the file to the destination.

        Arguments:
            destination: A filename (str) or file object to write to.
            buffer_size: Buffer size as used as length in
                :func:`shutil.copyfileobj`.
        """
        close_destination = False
        if isinstance(destination, str):
            destination = open(destination, "wb")
            close_destination = True
        try:
            copyfileobj(self.stream, destination, buffer_size)
        finally:
            if close_destination:
                destination.close()

    def close(self) -> None:
        try:
            self.stream.close()
        except Exception:
            pass

    def __bool__(self) -> bool:
        return bool(self.filename)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.stream, name)

    def __iter__(self) -> Iterable[bytes]:
        return iter(self.stream)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.filename} ({self.content_type}))>"
