from quart.datastructures import (
    ContentSecurityPolicy,
    HeaderSet,
    RequestAccessControl,
    ResponseAccessControl,
)


def test_content_security_policy() -> None:
    csp = ContentSecurityPolicy.from_header("font-src 'self'; media-src *")
    assert csp.font_src == "'self'"
    assert csp.media_src == "*"
    assert csp.to_header() == "font-src 'self'; media-src *"
    csp = ContentSecurityPolicy()
    csp.default_src = "* 'self' quart.com"
    csp.img_src = "'none'"
    assert csp.to_header() == "default-src * 'self' quart.com; img-src 'none'"


def test_header_set() -> None:
    updated = False

    def on_update(_: HeaderSet) -> None:
        nonlocal updated
        updated = True

    header_set = HeaderSet.from_header("GET, HEAD", on_update=on_update)
    assert header_set.to_header() in {"GET, HEAD", "HEAD, GET"}
    assert updated is False
    header_set.add("PUT")
    assert updated


def test_request_access_control() -> None:
    access_control = RequestAccessControl.from_headers(
        "http://quart.com", "X-Special, X-Other", "GET"
    )
    assert access_control.origin == "http://quart.com"
    assert access_control.request_method == "GET"
    assert access_control.request_headers == {"X-Special", "X-Other"}


def test_response_access_control() -> None:
    updated = False

    def on_update(_: HeaderSet) -> None:
        nonlocal updated
        updated = True

    access_control = ResponseAccessControl.from_headers(
        "true", "Cookie, X-Special", "GET, POST", "*", "Set-Cookie", "5", on_update
    )
    assert access_control.allow_credentials
    assert access_control.allow_headers == {"Cookie", "X-Special"}
    assert access_control.allow_methods == {"GET", "POST"}
    assert access_control.allow_origin == {"*"}
    assert access_control.expose_headers == {"Set-Cookie"}
    assert access_control.max_age == 5.0
    access_control.allow_methods.add("DELETE")
    access_control.allow_origin = HeaderSet(["https://quart.com"])
    assert updated
    assert access_control.allow_methods == {"GET", "POST", "DELETE"}
    assert access_control.allow_origin == {"https://quart.com"}
