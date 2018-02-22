from quart.datastructures import Accept, AcceptOption, CharsetAccept, LanguageAccept, MIMEAccept


def test_accept() -> None:
    accept = Accept(
        'application/vnd.google-earth.kml+xml;googleearth=context.kml,'
        'application/vnd.google-earth.kmz;googleearth=context.kmz;q=0.7'
    )
    assert accept.options == [
        AcceptOption(value='application/vnd.google-earth.kml+xml', quality=1.0),
        AcceptOption(value='application/vnd.google-earth.kmz', quality=0.7),
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
