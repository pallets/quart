import codecs
import io
import re
from cgi import parse_header
from datetime import datetime
from email.utils import parsedate_to_datetime
from functools import wraps
from shutil import copyfileobj
from typing import (
    Any, BinaryIO, Callable, Dict, Iterable, List, NamedTuple, Optional, Set, Type, Union,
)
from urllib.request import parse_http_list, parse_keqv_list
from wsgiref.handlers import format_date_time

from multidict import CIMultiDict as AIOCIMultiDict, MultiDict as AIOMultiDict


class _WerkzeugMultidictMixin:

    def get(self, key: str, default: Any=None, type: Any=None) -> Any:
        value = super().get(key, default)  # type: ignore
        if type is not None:
            try:
                value = type(value)
            except ValueError:
                value = default
        return value

    def getlist(self, key: str, type: Any=None) -> List[Any]:
        values = self.getall(key, [])  # type: ignore
        if type is not None:
            result = []
            for value in values:
                try:
                    result.append(type(value))
                except ValueError:
                    pass
            return result
        else:
            return values


class MultiDict(_WerkzeugMultidictMixin, AIOMultiDict):  # type: ignore
    pass


class CIMultiDict(_WerkzeugMultidictMixin, AIOCIMultiDict):  # type: ignore
    pass


def _unicodify(value: Any) -> str:
    try:
        return value.decode()  # type: ignore
    except AttributeError:
        return str(value)


class Headers(CIMultiDict):
    # Headers should accept byte keys and values but convert them to
    # unicode whilst stored. Note only a select few methods do this,
    # the others will error if presented with byte keys.

    def add(self, key: Any, value: Any) -> None:
        super().add(_unicodify(key), _unicodify(value))

    def __setitem__(self, key: Any, value: Any) -> None:
        super().__setitem__(_unicodify(key), _unicodify(value))

    def setdefault(self, key: Any, default: Optional[Any]=None) -> Optional[str]:
        return super().setdefault(_unicodify(key), _unicodify(default))


class FileStorage:
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
    parameters: dict


class Accept:

    def __init__(self, header_value: str) -> None:
        self.options: List[AcceptOption] = []
        for accept_option in parse_http_list(header_value):
            option, params = parse_header(accept_option)
            quality = float(params.pop('q', 1.0))
            self.options.append(AcceptOption(option, quality, params))

    def best_match(self, matches: List[str], default: Optional[str]=None) -> Optional[str]:
        best_match = AcceptOption(default, -1.0, {})
        for possible_match in matches:
            for option in self.options:
                if (
                        self._values_match(possible_match, option.value) and
                        option.quality > best_match.quality
                ):
                    best_match = AcceptOption(possible_match, option.quality, {})
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


class _CacheDirective:

    def __init__(self, name: str, converter: Callable) -> None:
        self.name = name
        self.converter = converter

    def __get__(self, instance: object, owner: type=None) -> Any:
        if instance is None:
            return self
        result = instance._directives[self.name]  # type: ignore
        return self.converter(result)

    def __set__(self, instance: object, value: Any) -> None:
        instance._directives[self.name] = self.converter(value)  # type: ignore
        if instance._on_update is not None:  # type: ignore
            instance._on_update(instance)  # type: ignore


class _CacheControl:
    no_cache = _CacheDirective('no-cache', bool)
    no_store = _CacheDirective('no-store', bool)
    no_transform = _CacheDirective('no-transform', bool)
    max_age = _CacheDirective('max-age', int)

    def __init__(self, on_update: Optional[Callable]=None) -> None:
        self._on_update = on_update
        self._directives: Dict[str, Any] = {}

    @classmethod
    def from_header(
            cls: Type['_CacheControl'],
            header: str,
            on_update: Optional[Callable]=None,
    ) -> '_CacheControl':
        cache_control = cls(on_update)
        for item in parse_http_list(header):
            if '=' in item:
                for key, value in parse_keqv_list([item]).items():
                    cache_control._directives[key] = value
            else:
                cache_control._directives[item] = True
        return cache_control

    def to_header(self) -> str:
        header = ''
        for directive, value in self._directives.items():
            if isinstance(value, bool):
                if value:
                    header += f"{directive},"
            else:
                header += f"{directive}={value},"
        return header.strip(',')


class RequestCacheControl(_CacheControl):
    max_stale = _CacheDirective('max-stale', int)
    min_fresh = _CacheDirective('min-fresh', int)
    no_transform = _CacheDirective('no-transform', bool)
    only_if_cached = _CacheDirective('only-if-cached', bool)


class ResponseCacheControl(_CacheControl):
    must_revalidate = _CacheDirective('must-revalidate', bool)
    private = _CacheDirective('private', bool)
    proxy_revalidate = _CacheDirective('proxy-revalidate', bool)
    public = _CacheDirective('public', bool)
    s_maxage = _CacheDirective('s-maxage', int)


class ETags:

    def __init__(
            self,
            weak: Optional[Set[str]]=None,
            strong: Optional[Set[str]]=None,
            star: bool=False,
    ) -> None:
        self.weak = weak or set()
        self.strong = strong or set()
        self.star = star

    def __contains__(self, etag: str) -> bool:
        return self.star or etag in self.strong

    @classmethod
    def from_header(cls: Type['ETags'], header: str) -> 'ETags':
        header = header.strip()
        weak = set()
        strong = set()
        if header == '*':
            return ETags(star=True)
        else:
            for item in parse_http_list(header):
                if item.upper().startswith('W/'):
                    weak.add(item[2:].strip('"'))
                else:
                    strong.add(item.strip('"'))
            return ETags(weak, strong)

    def to_header(self) -> str:
        if self.star:
            return '*'
        else:
            header = ''
            for tag in self.weak:
                header += f"W/\"{tag}\","
            for tag in self.strong:
                header += f"\"{tag}\","
            return header.strip(',')


class IfRange:

    def __init__(self, etag: Optional[str]=None, date: Optional[datetime]=None) -> None:
        self.etag = etag
        self.date = date

    @classmethod
    def from_header(cls: Type['IfRange'], header: str) -> 'IfRange':
        try:
            return IfRange(date=parsedate_to_datetime(header))
        except TypeError:  # Not a date format
            return IfRange(etag=header.strip('"'))

    def to_header(self) -> str:
        if self.etag is not None:
            return f"\"{self.etag}\""
        elif self.date is not None:
            return format_date_time(self.date.timestamp())
        else:
            return ''


class RangeSet(NamedTuple):
    begin: int
    end: Optional[int]


class Range:

    def __init__(self, units: str, ranges: List[RangeSet]) -> None:
        self.units = units
        self.ranges = ranges

    @classmethod
    def from_header(cls: Type['Range'], header: str) -> 'Range':
        try:
            units, raw_ranges = header.split('=', 1)
        except ValueError:
            return cls('', [])

        units = units.strip().lower()
        ranges = []
        for range_set in parse_http_list(raw_ranges):
            if range_set.startswith('-'):
                ranges.append(RangeSet(int(range_set), None))
            elif '-' in range_set:
                begin, end = range_set.split('-')
                ranges.append(RangeSet(int(begin), int(end)))
            else:
                ranges.append(RangeSet(0, int(range_set)))
        return Range(units, ranges)

    def to_header(self) -> str:
        header = f"{self.units}="
        for range_set in self.ranges:
            header += f"{range_set.begin}"
            if range_set.end is not None:
                header += f"-{range_set.end}"
            header += ','
        return header.strip(',')


def _on_update(method: Callable) -> Callable:
    @wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = method(self, *args, **kwargs)
        if self.on_update is not None:
            self.on_update(self)
        return result
    return wrapper


class HeaderSet(set):

    def __init__(self, *args: Any, on_update: Optional[Callable]=None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.on_update = on_update

    def to_header(self) -> str:
        header = ', '.join(self)
        return header.strip(',')

    @classmethod
    def from_header(
            cls: Type['HeaderSet'],
            header: str,
            on_update: Optional[Callable]=None,
    ) -> 'HeaderSet':
        items = {item for item in parse_http_list(header)}
        return cls(items, on_update=on_update)

    add = _on_update(set.add)
    clear = _on_update(set.clear)
    pop = _on_update(set.pop)
    remove = _on_update(set.remove)
    update = _on_update(set.update)


class _ContentRangeSpec:

    def __init__(self, name: str, converter: Callable) -> None:
        self.name = name
        self.converter = converter

    def __get__(self, instance: object, owner: type=None) -> Any:
        if instance is None:
            return self
        result = instance._specs.get(self.name)  # type: ignore
        if result is not None:
            return self.converter(result)
        else:
            return None

    def __set__(self, instance: object, value: Any) -> None:
        instance._specs[self.name] = value  # type: ignore
        if instance._on_update is not None:  # type: ignore
            instance._on_update(instance)  # type: ignore


class ContentRange:
    units = _ContentRangeSpec('units', str)
    start = _ContentRangeSpec('start', int)
    stop = _ContentRangeSpec('stop', int)
    length = _ContentRangeSpec('length', int)

    def __init__(
            self,
            units: Optional[str],
            start: Optional[int],
            stop: Optional[int],
            length: Optional[Union[int, str]]=None,
            on_update: Optional[Callable]=None,
    ) -> None:
        self._on_update = on_update
        self._specs: Dict[str, Any] = {}
        self.units = units
        self.start = start
        self.stop = stop
        self.length = length

    @classmethod
    def from_header(
            cls: Type['ContentRange'],
            header: str,
            on_update: Optional[Callable]=None,
    ) -> 'ContentRange':
        try:
            units, range_spec = header.split(None, 1)
        except ValueError:
            return cls(None, None, None)

        try:
            range_, length = range_spec.split('/', 1)
        except ValueError:
            return cls(None, None, None)

        if range_ == '*':
            return cls(units, None, None, length, on_update)

        try:
            start, stop = range_.split('-', 1)
            start = int(start)  # type: ignore
            stop = int(stop)  # type: ignore
        except ValueError:
            return cls(None, None, None)

        return cls(units, start, stop, length, on_update)  # type: ignore

    def to_header(self) -> str:
        if self.units is None:
            return ''
        length = self.length or '*'
        if self.start is None:
            return f"{self.units} */{length}"
        else:
            return f"{self.units} {self.start}-{self.stop}/{length}"


class RequestAccessControl:

    def __init__(self, origin: str, request_headers: HeaderSet, request_method: str) -> None:
        self.origin = origin
        self.request_headers = request_headers
        self.request_method = request_method

    @classmethod
    def from_headers(
            cls: Type['RequestAccessControl'],
            origin_header: str,
            request_headers_header: str,
            request_method_header: str,
    ) -> 'RequestAccessControl':
        request_headers = HeaderSet.from_header(request_headers_header)
        return cls(origin_header, request_headers, request_method_header)


class _AccessControlDescriptor:

    def __init__(self, name: str) -> None:
        self.name = name

    def __get__(self, instance: object, owner: type=None) -> Any:
        if instance is None:
            return self
        return instance._controls[self.name]  # type: ignore

    def __set__(self, instance: object, value: Any) -> None:
        header_set = HeaderSet(value, on_update=instance.on_update)  # type: ignore
        instance._controls[self.name] = header_set  # type: ignore
        if instance.on_update is not None:  # type: ignore
            instance.on_update()  # type: ignore


class ResponseAccessControl:
    allow_headers = _AccessControlDescriptor('allow_headers')
    allow_methods = _AccessControlDescriptor('allow_methods')
    allow_origin = _AccessControlDescriptor('allow_origin')
    expose_headers = _AccessControlDescriptor('expose_headers')

    def __init__(
            self,
            allow_credentials: Optional[bool],
            allow_headers: HeaderSet,
            allow_methods: HeaderSet,
            allow_origin: HeaderSet,
            expose_headers: HeaderSet,
            max_age: Optional[float],
            on_update: Optional[Callable]=None,
    ) -> None:
        self._on_update = None
        self._controls: Dict[str, Any] = {}
        self.allow_credentials = allow_credentials
        self.allow_headers = allow_headers
        self.allow_methods = allow_methods
        self.allow_origin = allow_origin
        self.expose_headers = expose_headers
        self.max_age = max_age
        self._on_update = on_update

    @property
    def allow_credentials(self) -> bool:
        return self._controls['allow_credentials'] is True

    @allow_credentials.setter
    def allow_credentials(self, value: Optional[bool]=None) -> None:
        self._controls['allow_credentials'] = value
        self.on_update()

    @property
    def max_age(self) -> Optional[float]:
        return self._controls['max_age']

    @max_age.setter
    def max_age(self, value: Optional[float]=None) -> None:
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = None
        self._controls['max_age'] = value
        self.on_update()

    @classmethod
    def from_headers(
            cls: Type['ResponseAccessControl'],
            allow_credentials_header: str,
            allow_headers_header: str,
            allow_methods_header: str,
            allow_origin_header: str,
            expose_headers_header: str,
            max_age_header: str,
            on_update: Optional[Callable]=None,
    ) -> 'ResponseAccessControl':
        allow_credentials = allow_credentials_header == 'true'
        allow_headers = HeaderSet.from_header(allow_headers_header)
        allow_methods = HeaderSet.from_header(allow_methods_header)
        allow_origin = HeaderSet.from_header(allow_origin_header)
        expose_headers = HeaderSet.from_header(expose_headers_header)
        try:
            max_age = float(max_age_header)
        except (ValueError, TypeError):
            max_age = None
        return cls(
            allow_credentials, allow_headers, allow_methods, allow_origin, expose_headers, max_age,
            on_update,
        )

    def on_update(self, _: Any=None) -> None:
        if self._on_update is not None:
            self._on_update(self)
