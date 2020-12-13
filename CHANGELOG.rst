0.14.1 2020-12-13
-----------------

* Bugfix add missing receive to test request connection and docs.
* Bugfix Add the templates_auto_reload API.
* Bugfix setting the debug property on the app now also sets the auto
  reloading for the jinja environment.

0.14.0 2020-12-05
-----------------

* Add user_agent property to requests/websockets - to easily extract
  the user agent using Werkzeug's UserAgent class.
* Bugfix set the content length when using send file - instead of
  using chunked transfer encoding.
* Introduce a test_app method - this should be used to ensure that
  the startup & shutdown functions are run during testing.
* Bugfix prevent local data sharing.
* Officially support Python 3.9.
* Add send and receive json to the test websocket client - allows a
  simpler way for json to be sent and received using the app's encoder
  and decoder.
* Add signals for websocket message receipt and sending - specifically
  the ``websocket_received`` and ``websocket_sent`` signals.
* Add dump and load functions to the json module - as matching Flask.
* Enhance the dev server output.
* Change AppContext lifespan interaction - this pushes the app context
  on startup and pops on shutdown meaning ``g`` is available
  throughout without being cleared.
* Major refactor of the testing system - this ensures that any
  middleware and lifespans are correctly tested. It also introduces a
  ``request`` method on the test client for a request connection (like
  the websocket connection) for testing streaming.

0.13.1 2020-09-09
-----------------

* Bugfix add the data property to the patched request attributes.
* Bugfix WebSocket ASGI rejection (for servers that don't support the
  ASGI WebSocket response extension).
* Bugfix don't wrap commands in with_appcontext by default.
* Bugfix CSP parsing for the report-only header.
* Bugfix wait for tasks to complete when cancelled.
* Bugfix clean up the generator when the response exits.
* Bugfix request data handling with Flask-Patch.

0.13.0 2020-07-14
-----------------

* Bugfix set cookies from the testing jar for websockets.
* Restore Flask-Patch sync handling to pre 0.11. This means that sync
  route handlers, before request, and more, are **not** run in a
  thread if Flask-Patch is used. This restores Flask-SQLAlchemy
  support (with Flask-Patch).
* Bugfix accept additional attributes to the delete cookie.

0.12.0 2020-05-21
-----------------

* Add certfile and keyfile arguments to cli.
* Bugfix request host value returns an empty string rather than None
  for HTTP/1.0 requests without a host header.
* Bugfix type of query string argument to Werkzeug Map fixing a
  TypeError.
* Add ASGI scope dictionary to request.
* Ensure that FlaskGroup exists when using flask_patch by patchin the
  flask.cli module from quart.
* Add quart.cli.with_appcontext matching the Flask API.
* Make the quart.Blueprint registration api compatible with
  flask.Blueprint.
* Make the add_url_rule api match the flask API.
* Resolve error handlers by most specific first (matches Flask).
* Support test sessions and context preservation when testing.
* Add lookup_app and lookup_request to flask patch globals.
* Make quart.Blueprint API constructor fully compatible with
  flask.Blueprint
* Bugfix ensure (url) defaults aren't copied between blueprint routes.

0.11.5 2020-03-31
-----------------

* Bugfix ensure any exceptions are raised in the ASGI handling code.
* Bugfix support url defaults in the blueprint API.

0.11.4 2020-03-29
-----------------

* Bugfix add a testing patch to ensure FlaskClient exists.
* Security/Bugfix htmlsafe function.
* Bugfix default to the map's strict slashes setting.
* Bugfix host normalisation for route matching.
* Bugfix add subdomain to the blueprint API.

0.11.3 2020-02-26
-----------------

* Bugfix lowercase header names passed to cgi FieldStorage.

0.11.2 2020-02-10
-----------------

* Bugfix debug traceback rendering.
* Bugfix multipart/form-data parsing.
* Bugfix uncomment cookie parameters.
* Bugfix add await to the LocalProxy mappings.

0.11.1 2020-02-09
-----------------

* Bugfix cors header accessors and setters.
* Bugfix iscoroutinefunction with Python3.7.
* Bugfix after request/websocket function typing.

0.11.0 2020-02-08
-----------------

*This contains all the Bugfixes in the 0.6 branch.*

* Allow relative root_path values.
* Add a TooManyRequests, 429, exception.
* Run synchronous code via a Thread Pool Executor. This means that
  sync route handlers, before request, and more, are run in a
  thread. **This is a major change.**
* Add an asgi_app method for middleware usage, for example
  ``quart_app.asgi_app = Middleware(quart_app.asgi_app)``.
* Add a ``run_sync`` function to run synchronous code in a thread
  pool with the Quart contexts present.
* Bugfix set cookies on redirects when testing.
* Bugfix follow the Flask API for dumps/loads.
* Support loading configuration with a custom loader, ``from_file``
  this allows for toml format configurations (among others).
* Bugfix match the Werkzeug API in redirect.
* Bugfix Respect QUART_DEBUG when using ``quart run``.
* Follow the Flask exception propagation rules, ensuring exceptions
  are propogated in testing.
* Support Python 3.8.
* Redirect with a 308 rather than 301 (following Flask/Werkzeug).
* Add a _QUART_PATCHED marker to all patched modules.
* Bugfix ensure multiple cookies are respected during testing.
* Switch to Werkzeug for datastructures and header parsing and
  dumping. **This is a major change.**
* Make the lock class customisable by the app subclass, this allows
  Quart-Trio to override the lock type.
* Add a run_task method to Quart (app) class. This is a task based on
  the run method assumptions that can be awaited or run as desired.
* Switch JSON tag datetime format to allow reading of Flask encoded
  tags.
* Switch to Werkzeug's cookie code. **This is a major change.**
* Switch to Werkzeug's routing code. **This is a major change.**
* Add signal handling to run method, but not the run_task method.

0.6.15 2019-10-17
-----------------

**This is the final 0.6 release and the final release to support Python3.6, Python3.8 is now available.**

* Bugfix handle 'http.request' without a 'body' key

0.10.0 2019-08-30
-----------------

*This contains all the Bugfixes in the 0.6 branch.*

* Support aborting with a Response argument.
* Fix JSON type hints to match typeshed.
* Update to Hypercorn 0.7.0 as minimum version.
* Bugfix ensure the default response timeout is set.
* Allow returning dictionaries from view functions, this follows a new
  addition to Flask.
* Bugfix ensure the response timeout has a default.
* Bugfix correct testing-websocket typing.
* Accept json, data, or form arguments to test_request_context.
* Support send_file sending a BytesIO object.
* Add samesite cookie support (requires Python3.8).
* Add a ContentSecurityPolicy datastructure, this follows a new
  addition to Werkzeug.
* Unblock logging I/O by logging in separate threads.
* Support ASGI root_path as a prepended path to all routes.

0.6.14 2019-08-30
-----------------

* Bugfix follow Werkzeug LocalProxy name API.
* Bugfix ensure multiple files are correctly loaded.
* Bugfix ensure make_response status code is an int.
* Bugfix be clear about header encoding.
* Bugfix ensure loading form/files data is timeout protected.
* Bugfix add missing Unauthorized, Forbidden, and NotAcceptable
  exception classes.

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
