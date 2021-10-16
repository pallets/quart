.. _background_task_discussion:

Background tasks
================

The API for background tasks follows Sanic and Starlette by taking a
callable and arguments. However, Quart will ensure that the tasks
finish during the shutdown (unless the server times out and
cancels). This is as you'd hope in a production environment.

Errors raised in a background task are logged but otherwise ignored
allowing the app to continue - much like with request/websocket
handling errors.
