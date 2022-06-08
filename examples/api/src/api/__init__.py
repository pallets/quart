from dataclasses import dataclass
from datetime import datetime

from quart import Quart, request
from quart_schema import QuartSchema, validate_request, validate_response

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
