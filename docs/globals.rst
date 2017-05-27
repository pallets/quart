.. _globals:

Globals
=======

As Quart follows the Flask API, it also has globals, specifically
``current_app, g, request, session``. These are globals as they are
likely needed in all request handlers.

Locals
------

As is rather confusing from a naming point of view, the globals are
local to the task being executed. This is detailed from a contextual
view in contexts_. This is necessary to ensure that Quart can
asynchronously handle many requests with a single global object.
