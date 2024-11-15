# Quart

![](https://raw.githubusercontent.com/pallets/quart/main/artwork/logo.png)

Quart is an async Python web application framework. Using Quart you can,

- render and serve HTML templates,
- write (RESTful) JSON APIs,
- serve WebSockets,
- stream request and response data,
- do pretty much anything over the HTTP or WebSocket protocols.

## Quickstart

Install from PyPI using an installer such as pip.

```
$ pip install quart
```

Save the following as `app.py`. This shows off rendering a template, returning
JSON data, and using a WebSocket.

```python
from quart import Quart, render_template, websocket

app = Quart(__name__)

@app.route("/")
async def hello():
    return await render_template("index.html")

@app.route("/api")
async def json():
    return {"hello": "world"}

@app.websocket("/ws")
async def ws():
    while True:
        await websocket.send("hello")
        await websocket.send_json({"hello": "world"})
```

```
$ quart run
 * Running on http://127.0.0.1:5000 (CTRL + C to quit)
```

To deploy this app in a production setting see the [deployment] documentation.

[deployment]: https://quart.palletsprojects.com/en/latest/tutorials/deployment.html

## Contributing

Quart is developed on [GitHub]. If you come across a bug, or have a feature
request, please open an [issue]. To contribute a fix or implement a feature,
follow our [contributing guide].

[GitHub]: https://github.com/pallets/quart
[issue]: https://github.com/pallets/quart/issues
[contributing guide]: https://github.com/pallets/quart/CONTRIBUTING.rst

## Help

If you need help with your code, the Quart [documentation] and [cheatsheet] are
the best places to start. You can ask for help on the [Discussions tab] or on
our [Discord chat].

[documentation]: https://quart.palletsprojects.com
[cheatsheet]: https://quart.palletsprojects.com/en/latest/reference/cheatsheet.html
[Discussions tab]: https://github.com/pallets/quart/discussions
[Discord chat]: https://discord.gg

## Relationship with Flask

Quart is an asyncio reimplementation of the popular [Flask] web application
framework. This means that if you understand Flask you understand Quart.

Like Flask, Quart has an ecosystem of extensions for more specific needs. In
addition, a number of the Flask extensions work with Quart.

[Flask]: https://flask.palletsprojects.com

### Migrating from Flask

It should be possible to migrate to Quart from Flask by a find and replace of
`flask` to `quart` and then adding `async` and `await` keywords. See the
[migration] documentation for more help.

[migration]: https://quart.palletsprojects.com/en/latest/how_to_guides/flask_migration.html
