import codecs
import io
import re
from cgi import parse_header
from shutil import copyfileobj
from typing import Any, BinaryIO, Dict, Iterable, List, NamedTuple, Optional
from urllib.request import parse_http_list

from multidict import CIMultiDict as AIOCIMultiDict, MultiDict as AIOMultiDict


class MultiDict(AIOMultiDict):

    def getlist(self, key: str) -> List[Any]:
        return self.getall(key)


class CIMultiDict(AIOCIMultiDict):

    def getlist(self, key: str) -> List[Any]:
        return self.getall(key)


class FileStorage(object):
    """A thin wrapper over incoming files."""

    def __init__(
            self,
            stream: BinaryIO=None,
            filename: str=None,
            name: str=None,
            content_type: str=None,
            headers: Dict=None,
    ) -> None:
        self.name = name
        self.stream = stream or io.BytesIO()
        self.filename = filename
        if headers is None:
            headers = {}
        self.headers = headers
        if content_type is not None:
            headers['Content-Type'] = content_type

    @property
    def content_type(self) -> Optional[str]:
        """The content-type sent in the header."""
        return self.headers.get('Content-Type')

    @property
    def content_length(self) -> int:
        """The content-length sent in the header."""
        return int(self.headers.get('content-length', 0))

    @property
    def mimetype(self) -> str:
        """Returns the mimetype parsed from the Content-Type header."""
        return parse_header(self.headers.get('Content-Type'))[0]

    @property
    def mimetype_params(self) -> Dict[str, str]:
        """Returns the params parsed from the Content-Type header."""
        return parse_header(self.headers.get('Content-Type'))[1]

    def save(self, destination: BinaryIO, buffer_size: int=16384) -> None:
        """Save the file to the destination.

        Arguments:
            destination: A filename (str) or file object to write to.
            buffer_size: Buffer size as used as length in
                :func:`shutil.copyfileobj`.
        """
        close_destination = False
        if isinstance(destination, str):
            destination = open(destination, 'wb')
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


class Authorization:

    def __init__(
            self,
            cnonce: Optional[str]=None,
            nc: Optional[str]=None,
            nonce: Optional[str]=None,
            opaque: Optional[str]=None,
            password: Optional[str]=None,
            qop: Optional[str]=None,
            realm: Optional[str]=None,
            response: Optional[str]=None,
            uri: Optional[str]=None,
            username: Optional[str]=None,
    ) -> None:
        self.cnonce = cnonce
        self.nc = nc
        self.nonce = nonce
        self.opaque = opaque
        self.password = password
        self.qop = qop
        self.realm = realm
        self.response = response
        self.uri = uri
        self.username = username


class AcceptOption(NamedTuple):
    value: str
    quality: float


class Accept:

    def __init__(self, header_value: str) -> None:
        self.options: List[AcceptOption] = []
        for accept_option in parse_http_list(header_value):
            try:
                option, raw_quality = accept_option.split(';')
            except ValueError:
                option = accept_option
                quality = 1.0
            else:
                quality = float(raw_quality.split('=', 1)[-1])
            self.options.append(AcceptOption(option, quality))

    def best_match(self, matches: List[str], default: Optional[str]=None) -> Optional[str]:
        best_match = AcceptOption(default, -1.0)
        for possible_match in matches:
            for option in self.options:
                if (
                        self._values_match(possible_match, option.value) and
                        option.quality > best_match.quality
                ):
                    best_match = AcceptOption(possible_match, option.quality)
        return best_match.value

    def _values_match(self, lhs: str, rhs: str) -> bool:
        return rhs == '*' or lhs.lower() == rhs.lower()


class CharsetAccept(Accept):

    def _values_match(self, lhs: str, rhs: str) -> bool:
        try:
            lhs_normalised = codecs.lookup(lhs).name
        except LookupError:
            lhs_normalised = lhs.lower()

        try:
            rhs_normalised = codecs.lookup(rhs).name
        except LookupError:
            rhs_normalised = rhs.lower()

        return rhs == '*' or lhs_normalised == rhs_normalised


class LanguageAccept(Accept):

    def _values_match(self, lhs: str, rhs: str) -> bool:
        lhs_normalised = re.split(r'[_-]', lhs.lower())
        rhs_normalised = re.split(r'[_-]', rhs.lower())
        return rhs == '*' or lhs_normalised == rhs_normalised


class MIMEAccept(Accept):

    def _values_match(self, lhs: str, rhs: str) -> bool:
        if rhs == '*':
            rhs_normalised = ['*', '*']
        else:
            rhs_normalised = rhs.lower().split('/', 1)

        if lhs == '*':
            lhs_normalised = ['*', '*']
        else:
            try:
                lhs_normalised = lhs.lower().split('/', 1)
            except ValueError:
                return False

        full_wildcard_allowed = (
            lhs_normalised[0] == lhs_normalised[1] == '*' or
            rhs_normalised[0] == rhs_normalised[1] == '*'
        )
        wildcard_allowed = (
            lhs_normalised[0] == rhs_normalised[0] and
            lhs_normalised[1] == '*' or rhs_normalised[1] == '*'
        )
        match_allowed = lhs_normalised == rhs_normalised
        return full_wildcard_allowed or wildcard_allowed or match_allowed
