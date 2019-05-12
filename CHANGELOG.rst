0.9.1 2019-05-12
----------------

* Bugfix unquote the path in the test client, following the ASGI
  standard.
* Bugfix follow Werkzeug LocalProxy name API.
* Bugfix ensure multiple files are correctly loaded.

0.9.0 2019-04-22
----------------

*This contains all the Bugfixes in the 0.6 and 0.8 branches.*

* Highlight the traceback line of code when using the debug system.
* Bugfix ensure debug has an affect when passed to app run.
* Change the test_request_context arguments to match the test client
  open arguments.
* Bugfix form data loading limit type.
* Support async Session Interfaces (with continued support for sync
  interfaces).
* Added before_app_websocket, and after_app_websocket methods to the
  Blueprint.
* Support sending headers on WebSocket acceptance (this requires ASGI
  server support, the default Hypercorn supports this).
* Support async teardown functions (with continued support for sync
  functions).
* Match the Flask API argument order for send_file adding a mimetype
  argument and supporting attachment sending.
* Make the requested subprotocols available via the websocket class,
  ``websocket.requested_subprotocols``.
* Support session saving with WebSockets (errors for cookie sessions
  if the WebSocket connection has been accepted).
* Switch to be an ASGI 3 framework (this requires ASGI server support,
  the default Hypercorn supports this).
* Refactor push promise API, the removes the
  ``response.push_promises`` attribute.
* Aceept Path (types) throughout and switch to Path (types)
  internally.

0.6.13 2019-04-22
-----------------

* Bugfix multipart parsing.
* Added Map.iter_rules(endpoint) Method.
* Bugfix cope if there is no source code (when using the debug
  system).

0.8.1 2019-02-09
----------------

* Bugfix make the safe_join function stricter.
* Bugfix parse multipart form data correctly.
* Bugfix add missing await.

0.8.0 2019-01-29
----------------

*This contains all the Bugfixes in the 0.6 and 0.7 branches.*

* Bugfix raise an error if the loaded app is not a Quart instance.
* Remove unused AccessLogAtoms
* Change the Quart::run method interface, this reduces the available
  options for simplicity. See hypercorn for an extended set of
  deployment configuration.
* Utilise the Hypercorn serve function, requires Hypercorn >= 0.5.0.
* Added list_templates method to DispatchingJinjaLoader.
* Add additional methods to the Accept datastructure, specifically
  keyed accessors.
* Expand the abort functionality and signature, to allow for the
  description and name to be optionally specified.
* Add a make_push_promise function, to allow for push promises to be
  sent at any time during the request handling e.g. pre-emptive
  pushes.
* Rethink the Response Body structure to allow for more efficient
  handling of file bodies and the ability to extend how files are
  managed (for Quart-Trio and others).
* Add the ability to send conditional 206 responses. Optionally a
  response can be made conditional by awaiting the make_conditional
  method with an argument of the request range.
* Recommend Mangum for serverless deployments.
* Added instance_path and instance_relative_config to allow for an
  instance folder to be used.

0.6.12 2019-01-29
-----------------

* Bugfix raise a BadRequest if the body encoding is wrong.
* Limit Hypercorn to versions < 0.6.
* Bugfix matching of MIMEAccept values.
* Bugfix handle the special routing case of /.
* Bugfix ensure sync functions work with async signals.
* Bugfix ensure redirect location headers are full URLs.
* Bugfix ensure open ended Range header works.
* Bugfix ensure RequestEntityTooLarge errors are correctly raised.

0.7.2 2019-01-03
----------------

* Fix the url display bug.
* Avoid crash in flask_patch isinstance.
* Cope with absolute paths sent in the scope.

0.7.1 2018-12-18
----------------

* Bugfix Flask patching step definition.

0.7.0 2018-12-16
----------------

* Support only Python 3.7, see the 0.6.X releases for continued Python
  3.6 support.
* Introduce ContextVars for local storage.
* Change default redirect status code to 302.
* Support integer/float cookie expires.
* Specify cookie date format (differs to Flask).
* Remove the Gunicorn workers, please use a ASGI server instead.
* Remove Gunicorn compatibility.
* Introduce a Headers data structure.
* Implement follow_redirects in Quart test client.
* Adopt the ASGI lifespan protocol.

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
  signal receivers to be async (which is much more useful) but
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
