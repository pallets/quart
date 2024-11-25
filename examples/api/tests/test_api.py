from api import app
from api import TodoIn


async def test_echo() -> None:
    test_client = app.test_client()
    response = await test_client.post("/echo", json={"a": "b"})
    data = await response.get_json()
    assert data == {"extra": True, "input": {"a": "b"}}


async def test_create_todo() -> None:
    test_client = app.test_client()
    response = await test_client.post("/todos/", json=TodoIn(task="Abc", due=None))
    data = await response.get_json()
    assert data == {"id": 1, "task": "Abc", "due": None}
