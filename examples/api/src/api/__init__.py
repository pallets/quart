from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from quart_schema import QuartSchema
from quart_schema import validate_request
from quart_schema import validate_response

from quart import Quart
from quart import request

app = Quart(__name__)
QuartSchema(app)


@app.post("/echo")
async def echo():
    print(request.is_json, request.mimetype)
    data = await request.get_json()
    return {"input": data, "extra": True}


@dataclass
class TodoIn:
    task: str
    due: datetime | None


@dataclass
class Todo(TodoIn):
    id: int


@app.post("/todos/")
@validate_request(TodoIn)
@validate_response(Todo)
async def create_todo(data: Todo) -> Todo:
    return Todo(id=1, task=data.task, due=data.due)


def run() -> None:
    app.run()
