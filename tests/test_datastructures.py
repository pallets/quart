from typing import List, Type, Union

import pytest

from quart.datastructures import (
    _CacheControl, Accept, AcceptOption, CharsetAccept, CIMultiDict, ContentRange, ETags,
    Headers, HeaderSet, LanguageAccept, MIMEAccept, MultiDict, Range, RangeSet,
    RequestAccessControl, RequestCacheControl, ResponseAccessControl, ResponseCacheControl,
)


@pytest.mark.parametrize('dict_class', [CIMultiDict, MultiDict])
def test_multidict_getlist(dict_class: Union[Type[CIMultiDict], Type[MultiDict]]) -> None:
    data = dict_class()
    data.add('x', 'y')
    data.add('x', 'z')
    assert data.getlist('x') == ['y', 'z']
    assert data.getlist('z') == []


@pytest.mark.parametrize('dict_class', [CIMultiDict, MultiDict])
def test_multidict_type_conversion(dict_class: Union[Type[CIMultiDict], Type[MultiDict]]) -> None:
    data = dict_class()
    data['x'] = '2'
    data['y'] = 'b'
    data.add('z', '2')
    data.add('z', 'b')
    assert data.get('x', type=int) == 2
    assert data.get('y', default=None, type=int) is None
    assert data.getlist('z', type=int) == [2]


@pytest.mark.parametrize('dict_class', [CIMultiDict, MultiDict])
def test_multidict_to_dict(dict_class: Union[Type[CIMultiDict], Type[MultiDict]]) -> None:
    data = dict_class()
    data['x'] = '2'
    data.add('z', '2')
    data.add('z', 'b')
    assert data.to_dict() == {'x': '2', 'z': 'b'}
    assert data.to_dict(flat=False) == {'x': ['2'], 'z': ['2', 'b']}


def test_headers_bytes() -> None:
    headers = Headers()
    headers[b'X-Foo'] = b'something'
    headers.add(b'X-Bar', b'something')
    headers.setdefault(b'X-Bob', 'something')

    assert headers['x-foo'] == 'something'
    assert headers['x-bar'] == 'something'
    assert headers['x-bob'] == 'something'
    headers.add('X-Foo', 'different')
    assert headers.getlist('X-Foo') == ['something', 'different']


def test_headers_non_strings() -> None:
    headers = Headers()
    headers['X-Foo'] = 12
    headers['X-Bar'] = True
    assert headers['x-foo'] == '12'
    assert headers['x-bar'] == 'True'


def test_headers_add_kwargs() -> None:
    headers = Headers()
    headers.add("Content-Disposition", "attachment", filename="abc")
    assert headers["content-disposition"] == "attachment; filename=abc"


def test_accept() -> None:
    accept = Accept(
        'application/vnd.google-earth.kml+xml;googleearth=context.kml,'
        'application/vnd.google-earth.kmz;googleearth=context.kmz;q=0.7'
    )
    assert accept.options == [
        AcceptOption('application/vnd.google-earth.kml+xml', 1.0, {'googleearth': 'context.kml'}),
        AcceptOption('application/vnd.google-earth.kmz', 0.7, {'googleearth': 'context.kmz'}),
    ]


def test_accept_best_match() -> None:
    accept = Accept('gzip, deflate, br;q=0.9, *;q=0.8')
    assert accept.best_match(['gzip', 'defalte']) == 'gzip'
    assert accept.best_match(['br', 'deflate']) == 'deflate'
    assert accept.best_match(['bizarre']) == 'bizarre'


def test_accept_quality() -> None:
    accept = Accept('gzip, deflate, br;q=0.9')
    assert accept.quality("gzip") == 1.0
    assert accept.quality("bizarre") == 0.0


def test_accept___getitem__() -> None:  # noqa: N807
    accept = Accept('gzip, deflate, br;q=0.9, *;q=0.8')
    assert accept["gzip"] == 1.0
    assert accept["bizarre"] == 0.8


def test_accept___contains__() -> None:  # noqa: N807
    accept = Accept('gzip, deflate, br;q=0.9, *;q=0.8')
    assert "gzip" in accept
    assert "bizzare" in accept


def test_charset_accept_best_match() -> None:
    accept = CharsetAccept('ISO-8859-1')
    assert accept.best_match(['ISO-8859-1']) == 'ISO-8859-1'


def test_language_accept_best_match() -> None:
    accept = LanguageAccept('en-GB,en-US;q=0.8,en;q=0.6')
    assert accept.best_match(['en-GB', 'en-US']) == 'en-GB'
    assert accept.best_match(['en']) == 'en'


def test_mime_accept_best_match() -> None:
    accept = MIMEAccept('text/html,application/xml;q=0.9,application/*;q=0.8,image/webp,*/*;q=0.7')
    assert accept.best_match(['text/html', 'image/webp']) == 'text/html'
    assert accept.best_match(['application/xml', 'text/html']) == 'text/html'
    assert accept.best_match(['application/jpg']) == 'application/jpg'
    assert accept.best_match(['bizarre/other']) == 'bizarre/other'

    accept = MIMEAccept('text/*')
    assert accept.best_match(['application/xml', 'text/html']) == 'text/html'


def test_cache_control() -> None:
    cache_control = _CacheControl()
    cache_control.no_cache = True
    cache_control.no_store = False
    cache_control.max_age = 2
    assert cache_control.to_header() == 'no-cache,max-age=2'


def test_request_cache_control() -> None:
    cache_control = RequestCacheControl.from_header('no-transform,no-cache,min-fresh=2')
    assert cache_control.no_transform is True
    assert cache_control.no_cache is True
    assert cache_control.min_fresh == 2  # type: ignore


def test_response_cache_control() -> None:
    updated = False

    def on_update(_: object) -> None:
        nonlocal updated
        updated = True

    cache_control = ResponseCacheControl.from_header('public, max-age=2592000', on_update)
    assert cache_control.public is True  # type: ignore
    assert cache_control.max_age == 2592000
    assert updated is False
    cache_control.max_age = 2
    assert updated is True


def test_etags() -> None:
    etags = ETags.from_header('W/"67ab43", "54ed21"')
    assert etags.weak == {'67ab43'}
    assert etags.strong == {'54ed21'}
    assert '54ed21' in etags
    assert etags.to_header() == 'W/"67ab43","54ed21"'


@pytest.mark.parametrize(
    "header, expected_ranges",
    [
        ("bytes=500-600,601-999", [RangeSet(500, 600), RangeSet(601, 999)]),
        ("bytes=-999", [RangeSet(-999, None)]),
        ("bytes=0-", [RangeSet(0, None)]),
    ],
)
def test_range(header: str, expected_ranges: List[RangeSet]) -> None:
    range_ = Range.from_header(header)
    assert range_.units == 'bytes'
    assert range_.ranges == expected_ranges
    assert range_.to_header() == header


def test_header_set() -> None:
    updated = False

    def on_update(_: HeaderSet) -> None:
        nonlocal updated
        updated = True

    header_set = HeaderSet.from_header('GET, HEAD', on_update=on_update)
    assert header_set.to_header() in {'GET, HEAD', 'HEAD, GET'}
    assert updated is False
    header_set.add('PUT')
    assert updated


def test_content_range() -> None:
    updated = False

    def on_update(_: HeaderSet) -> None:
        nonlocal updated
        updated = True

    content_range = ContentRange.from_header('bytes 0-499/1234', on_update=on_update)
    assert content_range.units == 'bytes'
    assert content_range.start == 0
    assert content_range.stop == 499
    assert content_range.length == 1234
    content_range.start = 734
    content_range.stop = 1233
    assert updated
    assert content_range.to_header() == 'bytes 734-1233/1234'


def test_request_access_control() -> None:
    access_control = RequestAccessControl.from_headers(
        'http://quart.com', 'X-Special, X-Other', 'GET',
    )
    assert access_control.origin == 'http://quart.com'
    assert access_control.request_method == 'GET'
    assert access_control.request_headers == {'X-Special', 'X-Other'}


def test_response_access_control() -> None:
    updated = False

    def on_update(_: HeaderSet) -> None:
        nonlocal updated
        updated = True

    access_control = ResponseAccessControl.from_headers(
        'true', 'Cookie, X-Special', 'GET, POST', '*', 'Set-Cookie', '5', on_update,
    )
    assert access_control.allow_credentials
    assert access_control.allow_headers == {'Cookie', 'X-Special'}
    assert access_control.allow_methods == {'GET', 'POST'}
    assert access_control.allow_origin == {'*'}
    assert access_control.expose_headers == {'Set-Cookie'}
    assert access_control.max_age == 5.0
    access_control.allow_methods.add('DELETE')
    access_control.allow_origin = HeaderSet(['https://quart.com'])
    assert updated
    assert access_control.allow_methods == {'GET', 'POST', 'DELETE'}
    assert access_control.allow_origin == {'https://quart.com'}
