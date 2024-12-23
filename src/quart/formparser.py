from __future__ import annotations

from collections.abc import Awaitable
from typing import Any
from typing import Callable
from typing import cast
from typing import IO
from typing import NoReturn
from typing import Optional
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl

from werkzeug.datastructures import Headers
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.formparser import default_stream_factory
from werkzeug.http import parse_options_header
from werkzeug.sansio.multipart import Data
from werkzeug.sansio.multipart import Epilogue
from werkzeug.sansio.multipart import Field
from werkzeug.sansio.multipart import File
from werkzeug.sansio.multipart import MultipartDecoder
from werkzeug.sansio.multipart import NeedData

from .datastructures import FileStorage

if TYPE_CHECKING:
    from .wrappers.request import Body

StreamFactory = Callable[
    [Optional[int], Optional[str], Optional[str], Optional[int]],
    IO[bytes],
]

ParserFunc = Callable[
    ["FormDataParser", "Body", str, Optional[int], dict[str, str]],
    Awaitable[tuple[MultiDict, MultiDict]],
]


class FormDataParser:
    file_storage_class = FileStorage

    def __init__(
        self,
        *,
        cls: type[MultiDict] | None = MultiDict,
        max_content_length: int | None = None,
        max_form_memory_size: int | None = None,
        max_form_parts: int | None = None,
        silent: bool = True,
        stream_factory: StreamFactory = default_stream_factory,
    ) -> None:
        self.cls = cls
        self.max_content_length = max_content_length
        self.max_form_memory_size = max_form_memory_size
        self.max_form_parts = max_form_parts
        self.silent = silent
        self.stream_factory = stream_factory

    def get_parse_func(
        self, mimetype: str, options: dict[str, str]
    ) -> ParserFunc | None:
        return self.parse_functions.get(mimetype)

    async def parse(
        self,
        body: Body,
        mimetype: str,
        content_length: int | None,
        options: dict[str, str] | None = None,
    ) -> tuple[MultiDict, MultiDict]:
        if options is None:
            options = {}

        parse_func = self.get_parse_func(mimetype, options)

        if parse_func is not None:
            try:
                return await parse_func(self, body, mimetype, content_length, options)
            except ValueError:
                if not self.silent:
                    raise

        return self.cls(), self.cls()

    async def _parse_multipart(
        self,
        body: Body,
        mimetype: str,
        content_length: int | None,
        options: dict[str, str],
    ) -> tuple[MultiDict, MultiDict]:
        parser = MultiPartParser(
            cls=self.cls,
            file_storage_cls=self.file_storage_class,
            max_content_length=self.max_content_length,
            max_form_memory_size=self.max_form_memory_size,
            max_form_parts=self.max_form_parts,
            stream_factory=self.stream_factory,
        )
        boundary = options.get("boundary", "").encode("ascii")

        if not boundary:
            raise ValueError("Missing boundary")

        return await parser.parse(body, boundary, content_length)

    async def _parse_urlencoded(
        self,
        body: Body,
        mimetype: str,
        content_length: int | None,
        options: dict[str, str],
    ) -> tuple[MultiDict, MultiDict]:
        try:
            form = parse_qsl(
                (await body).decode(),
                keep_blank_values=True,
                max_num_fields=self.max_form_parts,
            )
        except ValueError:
            raise RequestEntityTooLarge() from None
        return self.cls(form), self.cls()

    parse_functions: dict[str, ParserFunc] = {
        "multipart/form-data": _parse_multipart,
        "application/x-www-form-urlencoded": _parse_urlencoded,
        "application/x-url-encoded": _parse_urlencoded,
    }


class MultiPartParser:
    def __init__(
        self,
        *,
        buffer_size: int = 64 * 1024,
        cls: type[MultiDict] = MultiDict,
        file_storage_cls: type[FileStorage] = FileStorage,
        max_content_length: int | None = None,
        max_form_memory_size: int | None = None,
        max_form_parts: int | None = None,
        stream_factory: StreamFactory = default_stream_factory,
    ) -> None:
        self.buffer_size = buffer_size
        self.cls = cls
        self.file_storage_cls = file_storage_cls
        self.max_content_length = max_content_length
        self.max_form_memory_size = max_form_memory_size
        self.max_form_parts = max_form_parts
        self.stream_factory = stream_factory

    def fail(self, message: str) -> NoReturn:
        raise ValueError(message)

    def get_part_charset(self, headers: Headers) -> str:
        content_type = headers.get("content-type")

        if content_type:
            parameters = parse_options_header(content_type)[1]
            ct_charset = parameters.get("charset", "").lower()

            # A safe list of encodings. Modern clients should only send ASCII or UTF-8.
            # This list will not be extended further.
            if ct_charset in {"ascii", "us-ascii", "utf-8", "iso-8859-1"}:
                return ct_charset

        return "utf-8"

    def start_file_streaming(self, event: File, total_content_length: int) -> IO[bytes]:
        content_type = event.headers.get("content-type")

        try:
            content_length = int(event.headers["content-length"])
        except (KeyError, ValueError):
            content_length = 0

        container = self.stream_factory(
            total_content_length,
            content_type,
            event.filename,
            content_length,
        )
        return container

    async def parse(
        self, body: Body, boundary: bytes, content_length: int
    ) -> tuple[MultiDict, MultiDict]:
        container: IO[bytes] | list[bytes]
        _write: Callable[[bytes], Any]

        parser = MultipartDecoder(
            boundary, self.max_content_length, max_parts=self.max_form_parts
        )

        fields = []
        files = []

        current_part: Field | File
        field_size: int | None = None
        async for data in body:
            parser.receive_data(data)
            event = parser.next_event()
            while not isinstance(event, (Epilogue, NeedData)):
                if isinstance(event, Field):
                    current_part = event
                    field_size = 0
                    container = []
                    _write = container.append
                elif isinstance(event, File):
                    current_part = event
                    field_size = None
                    container = self.start_file_streaming(event, content_length)
                    _write = container.write
                elif isinstance(event, Data):
                    if self.max_form_memory_size is not None and field_size is not None:
                        field_size += len(event.data)

                        if field_size > self.max_form_memory_size:
                            raise RequestEntityTooLarge()

                    _write(event.data)
                    if not event.more_data:
                        if isinstance(current_part, Field):
                            value = b"".join(container).decode(
                                self.get_part_charset(current_part.headers), "replace"
                            )
                            fields.append((current_part.name, value))
                        else:
                            container = cast(IO[bytes], container)
                            container.seek(0)
                            files.append(
                                (
                                    current_part.name,
                                    self.file_storage_cls(
                                        container,
                                        current_part.filename,
                                        current_part.name,
                                        headers=current_part.headers,
                                    ),
                                )
                            )

                event = parser.next_event()

        return self.cls(fields), self.cls(files)
