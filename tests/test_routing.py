import uuid
from typing import Any, Dict, Tuple

import hypothesis.strategies as strategies
import pytest
from hypothesis import given

from quart.exceptions import BadRequest, MethodNotAllowed, NotFound, RedirectRequired
from quart.routing import (
    BuildError, FloatConverter, IntegerConverter, Map, Rule, StringConverter, UUIDConverter,
)


@pytest.fixture()
def basic_map() -> Map:
    map_ = Map()
    map_.add(Rule('/', {'POST'}, 'index'))
    map_.add(Rule('/', {'DELETE'}, 'delete_index'))
    map_.add(Rule('/leaf', {'GET'}, 'leaf'))
    map_.add(Rule('/branch/', {'GET'}, 'branch'))
    return map_


def test_basic_matching(basic_map: Map) -> None:
    _test_match(basic_map, '/', 'POST', (basic_map.endpoints['index'][0], {}))
    _test_match(basic_map, '/leaf', 'GET', (basic_map.endpoints['leaf'][0], {}))
    _test_match(basic_map, '/branch/', 'GET', (basic_map.endpoints['branch'][0], {}))


def _test_match(
        map_: Map, path: str, method: str, expected: Tuple[Rule, Dict[str, Any]],
        host: str='',
        websocket: bool=False,
        root_path: str="",
) -> None:
    adapter = map_.bind_to_request(False, host, method, path, b'', websocket, root_path)
    assert adapter.match() == expected


def _test_match_redirect(
        map_: Map, path: str, method: str, redirect_path: str, query_string: bytes=b'',
        host: str='',
) -> None:
    adapter = map_.bind_to_request(False, host, method, path, query_string, False, "")
    with pytest.raises(RedirectRequired) as error:
        adapter.match()
    assert error.value.redirect_path == f"http://{host}{redirect_path}"


def test_no_match_error(basic_map: Map) -> None:
    _test_no_match(basic_map, '/wrong/', 'GET')


def _test_no_match(map_: Map, path: str, method: str, root_path: str="") -> None:
    adapter = map_.bind_to_request(False, '', method, path, b'', False, root_path)
    with pytest.raises(NotFound):
        adapter.match()


def test_method_not_allowed_error(basic_map: Map) -> None:
    adapter = basic_map.bind_to_request(False, '', 'GET', '/', b'', False, "")
    try:
        adapter.match()
    except Exception as error:
        assert isinstance(error, MethodNotAllowed)
        assert error.allowed_methods == {'DELETE', 'POST'}


def test_basic_building(basic_map: Map) -> None:
    adapter = basic_map.bind(False, '')
    assert adapter.build('index', method='POST') == '/'
    assert adapter.build('delete_index', method='DELETE') == '/'
    assert adapter.build('leaf') == '/leaf'
    assert adapter.build('branch') == '/branch/'


def test_value_building() -> None:
    map_ = Map()
    map_.add(Rule('/book/<page>', {'GET'}, 'book'))
    adapter = map_.bind(False, '')
    assert adapter.build('book', values={'page': 1}) == '/book/1'
    assert adapter.build('book', values={'page': 1, 'line': 12}) == '/book/1?line=12'
    assert adapter.build('book', values={'page': 1, 'line': [1, 2]}) == '/book/1?line=1&line=2'


def test_build_error(basic_map: Map) -> None:
    basic_map.add(Rule('/values/<int:x>/', {'GET'}, 'values'))
    adapter = basic_map.bind(False, '')
    with pytest.raises(BuildError) as error:
        adapter.build('bob')
    assert 'No endpoint found' in str(error.value)
    with pytest.raises(BuildError) as error:
        adapter.build('values', values={'y': 2})
    assert 'do not match' in str(error.value)
    with pytest.raises(BuildError) as error:
        adapter.build('values', method='POST')
    assert 'not one of' in str(error.value)


def test_build_external() -> None:
    map_ = Map()
    map_.add(Rule('/ws/', {'GET'}, 'websocket', is_websocket=True))
    map_.add(Rule('/', {'GET'}, 'index'))
    adapter = map_.bind(True, 'localhost')
    adapter.build("websocket") == "wss://localhost/ws/"
    adapter.build("index") == "https://localhost/"


def test_strict_slashes() -> None:
    def _test_strict_slashes(map_: Map) -> None:
        adapter = map_.bind_to_request(False, '', 'POST', '/path/', b'', False, "")
        with pytest.raises(MethodNotAllowed):
            adapter.match()
        _test_match_redirect(map_, '/path', 'GET', '/path/')

    map_ = Map()
    map_.add(Rule('/path', {'POST'}, 'leaf'))
    map_.add(Rule('/path/', {'GET'}, 'branch'))
    # Ensure that the matching is invariant under reversed order of
    # addition to a Map.
    map_reversed = Map()
    map_reversed.add(Rule('/path', {'POST'}, 'leaf'))
    map_reversed.add(Rule('/path/', {'GET'}, 'branch'))

    _test_strict_slashes(map_)
    _test_strict_slashes(map_reversed)


def test_disabled_strict_slashes() -> None:
    map_ = Map()
    map_.add(Rule('/', {'GET'}, 'index', strict_slashes=False))
    _test_match(map_, '/', 'GET', (map_.endpoints['index'][0], {}))
    _test_match(map_, '//', 'GET', (map_.endpoints['index'][0], {}))
    map_.add(Rule('/foo', {'GET'}, 'foo', strict_slashes=False))
    _test_match(map_, '/foo', 'GET', (map_.endpoints['foo'][0], {}))
    _test_match(map_, '/foo/', 'GET', (map_.endpoints['foo'][0], {}))
    map_.add(Rule('/bar/', {'GET'}, 'bar', strict_slashes=False))
    _test_match(map_, '/bar', 'GET', (map_.endpoints['bar'][0], {}))
    _test_match(map_, '/bar/', 'GET', (map_.endpoints['bar'][0], {}))


def test_redirect_url_query_string() -> None:
    map_ = Map()
    map_.add(Rule('/path/', {'GET'}, 'branch'))
    _test_match_redirect(map_, '/path', 'GET', '/path/?a=b', b'a=b')


def test_redirect_url_host() -> None:
    map_ = Map(host_matching=True)
    map_.add(Rule('/path/', {'GET'}, 'branch', host='quart.com'))
    map_.add(Rule('/path/', {'GET'}, 'branch', host='flask.com'))
    _test_match_redirect(map_, '/path', 'GET', '/path/', host='quart.com')
    _test_match_redirect(map_, '/path', 'GET', '/path/', host='flask.com')


def test_ordering() -> None:
    map_ = Map()
    map_.add(Rule('/fixed', {'GET'}, 'fixed'))
    map_.add(Rule('/<path:path>', {'GET'}, 'path'))
    map_.add(Rule('/<path:left>/<path:right>', {'GET'}, 'path'))
    _test_match(map_, '/fixed', 'GET', (map_.endpoints['fixed'][0], {}))
    _test_match(map_, '/path', 'GET', (map_.endpoints['path'][1], {'path': 'path'}))
    _test_match(
        map_, '/left/right', 'GET', (map_.endpoints['path'][0], {'left': 'left', 'right': 'right'}),
    )


def test_defaults() -> None:
    map_ = Map()
    map_.add(Rule('/book/', {'GET'}, 'book', defaults={'page': 1}))
    map_.add(Rule('/book/<int:page>/', {'GET'}, 'book'))
    _test_match(map_, '/book/', 'GET', (map_.endpoints['book'][0], {'page': 1}))
    _test_match_redirect(map_, '/book/1/', 'GET', '/book/')
    _test_match(map_, '/book/2/', 'GET', (map_.endpoints['book'][1], {'page': 2}))
    adapter = map_.bind(False, '')
    assert adapter.build('book', method='GET') == '/book/'
    assert adapter.build('book', method='GET', values={'page': 1}) == '/book/'
    assert adapter.build('book', method='GET', values={'page': 2}) == '/book/2/'


def test_host() -> None:
    map_ = Map(host_matching=True)
    map_.add(Rule('/', {'GET'}, 'index'))
    map_.add(Rule('/', {'GET'}, 'subdomain', host='quart.com'))
    _test_match(map_, '/', 'GET', (map_.endpoints['index'][0], {}))
    _test_match(map_, '/', 'GET', (map_.endpoints['subdomain'][0], {}), host='quart.com')


def test_websocket() -> None:
    map_ = Map()
    map_.add(Rule("/ws/", {"GET"}, "http"))
    map_.add(Rule("/ws/", {"GET"}, "websocket", is_websocket=True))
    _test_match(map_, "/ws/", "GET", (map_.endpoints["http"][0], {}))
    _test_match(map_, "/ws/", "GET", (map_.endpoints["websocket"][0], {}), websocket=True)


def test_root_path_match() -> None:
    map_ = Map()
    map_.add(Rule("/", {"GET"}, "http"))
    _test_no_match(map_, "/", "GET", root_path="/rooti")
    _test_match(map_, "/rooti/", "GET", (map_.endpoints["http"][0], {}), root_path="/rooti")


def test_root_path_build() -> None:
    map_ = Map()
    map_.add(Rule("/", {"GET"}, "http"))
    adapter = map_.bind_to_request(False, "", "GET", "/", b'', False, "/rooti")
    assert adapter.build("http", method="GET") == "/rooti/"


@pytest.mark.parametrize("websocket", [True, False])
def test_websocket_bad_request(websocket: bool) -> None:
    map_ = Map()
    map_.add(Rule("/ws/", {"GET"}, "websocket", is_websocket=websocket))
    adapter = map_.bind_to_request(False, "", "GET", "/ws/", b"", not websocket, "")
    with pytest.raises(BadRequest):
        adapter.match()


def test_websocket_and_method_not_allowed() -> None:
    map_ = Map()
    map_.add(Rule("/ws/", {"GET"}, "websocket", is_websocket=True))
    map_.add(Rule("/ws/", {"POST"}, "post"))
    adapter = map_.bind_to_request(False, "", "PUT", "/ws/", b"", False, "")
    with pytest.raises(MethodNotAllowed):
        adapter.match()


def test_any_converter() -> None:
    map_ = Map()
    map_.add(Rule('/<any(about, "left,right", jeff):name>', {'GET'}, 'any'))
    _test_match(map_, '/about', 'GET', (map_.endpoints['any'][0], {'name': 'about'}))
    _test_match(map_, '/left,right', 'GET', (map_.endpoints['any'][0], {'name': 'left,right'}))
    _test_no_match(map_, '/other', 'GET')


def test_path_converter() -> None:
    map_ = Map()
    map_.add(Rule('/', {'GET'}, 'index'))
    map_.add(Rule('/constant', {'GET'}, 'constant'))
    map_.add(Rule('/<int:integer>', {'GET'}, 'integer'))
    map_.add(Rule('/<path:page>', {'GET'}, 'page'))
    map_.add(Rule('/<path:page>/constant', {'GET'}, 'page_constant'))
    map_.add(Rule('/<path:left>/middle/<path:right>', {'GET'}, 'double_page'))
    map_.add(Rule('/<path:left>/middle/<path:right>/constant', {'GET'}, 'double_page_constant'))
    map_.add(Rule('/Colon:<path:name>', {'GET'}, 'colon_path'))
    map_.add(Rule('/Colon:<name>', {'GET'}, 'colon_base'))
    _test_match(map_, '/', 'GET', (map_.endpoints['index'][0], {}))
    _test_match(map_, '/constant', 'GET', (map_.endpoints['constant'][0], {}))
    _test_match(map_, '/20', 'GET', (map_.endpoints['integer'][0], {'integer': 20}))
    _test_match(map_, '/branch/leaf', 'GET', (map_.endpoints['page'][0], {'page': 'branch/leaf'}))
    _test_match(
        map_, '/branch/constant', 'GET', (map_.endpoints['page_constant'][0], {'page': 'branch'}),
    )
    _test_match(
        map_, '/branch/middle/leaf', 'GET',
        (map_.endpoints['double_page'][0], {'left': 'branch', 'right': 'leaf'}),
    )
    _test_match(
        map_, '/branch/middle/leaf/constant', 'GET',
        (map_.endpoints['double_page_constant'][0], {'left': 'branch', 'right': 'leaf'}),
    )
    _test_match(
        map_, '/Colon:branch', 'GET', (map_.endpoints['colon_base'][0], {'name': 'branch'}),
    )
    _test_match(
        map_, '/Colon:branch/leaf', 'GET',
        (map_.endpoints['colon_path'][0], {'name': 'branch/leaf'}),
    )


@given(value=strategies.uuids())
def test_uuid_converter(value: uuid.UUID) -> None:
    converter = UUIDConverter()
    assert converter.to_python(converter.to_url(value)) == value


def test_uuid_converter_match() -> None:
    map_ = Map()
    map_.add(Rule('/<uuid:uuid>', {'GET'}, 'uuid'))
    _test_match(
        map_, '/a8098c1a-f86e-11da-bd1a-00112444be1e', 'GET',
        (map_.endpoints['uuid'][0], {'uuid': uuid.UUID('a8098c1a-f86e-11da-bd1a-00112444be1e')}),
    )


@given(value=strategies.integers())
def test_integer_converter(value: int) -> None:
    converter = IntegerConverter()
    assert converter.to_python(converter.to_url(value)) == value


def test_int_converter_match() -> None:
    map_ = Map()
    map_.add(Rule('/<int(min=5):value>', {'GET'}, 'min'))
    map_.add(Rule('/<int:value>', {'GET'}, 'any'))
    _test_match(map_, '/4', 'GET', (map_.endpoints['any'][0], {'value': 4}))
    _test_match(map_, '/6', 'GET', (map_.endpoints['min'][0], {'value': 6}))


@given(value=strategies.floats(allow_nan=False, allow_infinity=False))
def test_float_converter(value: float) -> None:
    converter = FloatConverter()
    assert converter.to_python(converter.to_url(value)) == value


def test_float_converter_match() -> None:
    map_ = Map()
    map_.add(Rule('/<float(max=1000.0):value>', {'GET'}, 'max'))
    map_.add(Rule('/<float:value>', {'GET'}, 'any'))
    _test_match(map_, '/1001.0', 'GET', (map_.endpoints['any'][0], {'value': 1001.0}))
    _test_match(map_, '/999.0', 'GET', (map_.endpoints['max'][0], {'value': 999.0}))


@given(value=strategies.characters(blacklist_characters=['/']))
def test_string_converter(value: str) -> None:
    converter = StringConverter()
    assert converter.to_python(converter.to_url(value)) == value


def test_string_converter_match() -> None:
    map_ = Map()
    map_.add(Rule('/<string(length=2):value>', {'GET'}, 'string'))
    _test_match(map_, '/uk', 'GET', (map_.endpoints['string'][0], {'value': 'uk'}))
    _test_no_match(map_, '/usa', 'GET')
