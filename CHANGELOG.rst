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
