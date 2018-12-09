0.6.11 2018-12-09
-----------------

* Bugfix support static files in blueprints.
* Bugfix ensure automatic options API matches Flask and works.
* Bugfix app.run SSL usage and Hypercorn compatibility.

0.6.10 2018-11-12
-----------------

* Bugfix async body iteration cleanup.

0.6.9 2018-11-10
----------------

* Bugfix async body iteration deadlock.
* Bufgix ASGI handling to ensure completion.

0.6.8 2018-10-21
----------------

* Ensure an event loop is specified on app.run.
* Bugfix ensure handler responses are finalized.
* Bugfix ensure the ASGI callable returns on completion.

0.6.7 2018-09-23
----------------

* Bugfix ASGI conversion of websocket data (str or bytes).
* Bugfix ensure redirect url includes host when host matching.
* Bugfix ensure query strings are present in redirect urls.
* Bugfix ensure header values are string types.
* Bugfix incorrect endpoint override error for synchronous view
  functions.

0.6.6 2018-08-27
----------------

* Bugfix add type conversion to getlist (on multidicts)
* Bugfix correct ASGI client usage (allows for None)
* Bugfix ensure overlapping requests work without destroying the
  others context.
* Bugfix ensure only integer status codes are accepted.

0.6.5 2018-08-05
----------------

* Bugfix change default redirect status code to 302.
* Bugfix support query string parsing from test client paths.
* Bugfix support int/float cookie expires values.
* Bugfix correct the cookie date format to RFC 822.
* Bugfix copy sys.modules to prevent dictionary changed errors.
* Bugfix ensure request body iteration returns all data.
* Bugfix correct set host header (if missing) for HTTP/1.0.
* Bugfix set the correct defaults for _external in url_for.

0.6.4 2018-07-15
----------------

* Bugfix correctly handle request query strings.
* Restore log output when running in development mode.
* Bugfix allow for multiple query string values when building urls,
  e.g. ``a=1&a=2``.
* Bugfix ensure the Flask Patch system works with Python 3.7.

0.6.3 2018-07-05
----------------

* Bugfix ensure compatibility with Python 3.7

0.6.2 2018-06-24
----------------

* Bugfix remove class member patching from flask-patch system, as was
  unreliable.
* Bugfix ensure ASGI websocket handler closes on disconnect.
* Bugfix cope with optional client values in ASGI scope.

0.6.1 2018-06-18
----------------

* Bugfix accept PathLike objects to the ``send_file`` function.
* Bugfix mutable methods in blueprint routes or url rule addition.
* Bugfix don't lowercase header values.
* Bugfix support automatic options on View classes.

0.6.0 2018-06-11
----------------

* Quart is now an ASGI framework, and requires an ASGI server to serve
  requests. `Hypercorn <https://gitlab.com/pgjones/hypercorn>`_ is
  used in development and is recommended for production. Hypercorn
  is a continuation of the Quart serving code.
* Add before and after serving functionality, this is provisional.
* Add caching, last modified and etag information to static files
  served via send_file.
* Bugfix date formatting in response headers.
* Bugfix make_response should error if response is None.
* Deprecate the Gunicorn workers, see ASGI servers (e.g. Uvicorn).
* Bugfix ensure shell context processors work.
* Change template context processors to be async, this is backwards
  incompatible.
* Change websocket API to be async, this is backwards incompatible.
* Allow the websocket class to be configurable by users.
* Bugfix catch signals on Windows.
* Perserve context in Flask-Patch system.
* Add the websocket API to blueprints.
* Add host, subdomain, and default options to websocket routes.
* Bugfix support defaults on route or add_url_rule usage.
* Introduce a more useful BuildError
* Bugfix match Flask after request function execution order.
* Support ``required_methods`` on view functions.
* Added CORS, Access Control, datastructures to request and response
  objects.
* Allow type conversion in (CI)MultiDict get.

0.5.0 2018-04-13
----------------

* Further API compatibility with Flask, specifically submodules,
  wrappers, and the app.
* Bugfix ensure error handlers work.
* Bugfix await get_data in Flask Patch system.
* Bugfix rule building, specifically additional arguments as query
  strings.
* Ability to add defaults to routes on definition.
* Bugfix allow set_cookie to accept bytes arguments.
* Bugfix ensure mimetype are returned.
* Add host matching, and subdomains for routes.
* Introduce implicit sequence conversion to response data.
* URL and host information on requests.
* Add a debug page, which shows tracebacks on errors.
* Bugfix accept header parsing.
* Bugfix cope with multi lists in forms.
* Add cache control, etag and range header structures.
* Add host, url, scheme and path correctly to path wrappers.
* Bugfix CLI module parsing.
* Add auto reloading on file changes.
* Bugfix ignore invalid upgrade headers.
* Bugfix h2c requests when there is a body (to not upgrade).
* Refactor of websocket API, matching the request API as an analogue.
* Refactor to mitigate DOS attacks, add documentation section.
* Allow event loop to be specified when running apps.
* Bugfix ensure automatic options work.
* Rename TestClient -> QuartClient to match Flask naming.

0.4.1 2018-01-27
----------------

* Bugfix HTTP/2 support and pass h2spec compliance testing.
* Bugifx Websocket support and pass autobahn fuzzy test compliance
  testing.
* Bugfix HEAD request support (don't try to send a body).
* Bugfix content-type (remove forced override).

0.4.0 2018-01-14
----------------

* Change to async signals and context management. This allows the
  signal recievers to be async (which is much more useful) but
  requires changes to any current usage (notably test contexts).
* Add initial support of websockets.
* Support HTTP/1.1 to HTTP/2 (h2c) upgrades, includes supporting
  HTTP/2 without SSL (note browsers don't support this).
* Add timing to access logging.
* Add a new Logo :). Thanks to @koddr.
* Support streaming of the request body.
* Add initial CLI support, using click.
* Add context copying helper functions and clarify how to stream a
  response.
* Improved tutorials.
* Allow the request to be limited to prevent DOS attacks.

0.3.1 2017-10-25
----------------

* Fix incorrect error message for HTTP/1.1 requests.
* Fix HTTP/1.1 pipelining support and error handling.

0.3.0 2017-10-10
----------------

* Change flask_ext name to flask_patch to clarify that it is not the
  pre-existing flask_ext system and that it patches Quart to provide
  Flask imports.
* Added support for views.
* Match Werkzeug API for FileStorage.
* Support HTTP/2 pipelining.
* Add access logging.
* Add HTTP/2 Server push, see the ``push_promises`` Set on a Response
  object.
* Add idle timeouts.

0.2.0 2017-07-22
----------------

This is still an alpha version of Quart, some notable changes are,

* Support for Flask extensions via the flask_ext module (if imported).
* Initial documentation setup and actual documentation including API
  docstrings.
* Closer match to the Flask API, most modules now match the Flask
  public API.

0.1.0 2017-05-21
----------------

* Released initial pre alpha version.
