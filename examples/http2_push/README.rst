PythonTiles
===========

This is an example inspired by `GopherTiles <https://http2.golang.org/gophertiles>`_ demonstrating Quart's HTTP/2 push promise capabilities.

This example requires the `Pillow library <https://pypi.org>`_

- `pip install -r requirements.txt`
- `QUART_APP=http2_push quart run`

The application exposes two endpoints:

- `https://localhost:5000/` using standard HTTP/2
- `https://localhost:5000/push` using HTTP/2 push promises
