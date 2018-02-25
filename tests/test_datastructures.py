from quart.datastructures import (
    _CacheControl, Accept, AcceptOption, CharsetAccept, ETags, LanguageAccept, MIMEAccept,
    Range, RangeSet, RequestCacheControl, ResponseCacheControl,
)


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


def test_range() -> None:
    range_ = Range.from_header('bytes=500-600,601-999')
    assert range_.units == 'bytes'
    assert range_.ranges == [RangeSet(500, 600), RangeSet(601, 999)]
    assert range_.to_header() == 'bytes=500-600,601-999'
    range_ = Range.from_header('bytes=-999')
    assert range_.units == 'bytes'
    assert range_.ranges == [RangeSet(-999, None)]
    assert range_.to_header() == 'bytes=-999'
