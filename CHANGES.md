## Version 0.20.0

Released 2024-12-23

- Drop support for Python 3.8.
- Fix deprecated `asyncio.iscoroutinefunction` for Python 3.14.
- Allow `AsyncIterable` to be passed to `Response`.
- Support max_form_parts and max_form_memory_size.

## Version 0.19.9

Released 2024-11-14

- Fix missing `PROVIDE_AUTOMATIC_OPTIONS` config for compatibility with
  Flask 3.1.

## Version 0.19.8

Released 2024-10-25

- Fix missing check that caused the previous fix to raise an error.

## Version 0.19.7

Released 2024-10-25

- Fix how `max_form_memory_size` is applied when parsing large non-file fields.
  <https://github.com/advisories/GHSA-q34m-jh98-gwm2>

## Version 0.19.6

Released 2024-05-19

- Use `ContentRange` in the right way.
- Hold a strong reference to background tasks.
- Avoid `ResourceWarning` in `DataBody.__aiter__`.

## Version 0.19.5

Released 2024-04-01

- Address `DeprecationWarning` from `datetime.utcnow()`.
- Ensure request files are closed.
- Fix development server restarting when commands are passed.
- Restore `teardown_websocket` methods.
- Correct the `config_class` type.
- Allow `kwargs` to be passed to the test client (matches Flask API).

## Version 0.19.4

Released 2023-11-19

- Fix program not closing on Ctrl+C in Windows.
- Fix the typing for `AfterWebsocket` functions.
- Improve the typing of the `ensure_async` method.
- Add a shutdown event to the app.

## Version 0.19.3

Released 2023-10-04

- Update the default config to better match Flask.

## Version 0.19.2

Released 2023-10-01

- Restore the app `after_`/`before_websocket` methods.
- Correctly set the `cli` group in Quart.

## Version 0.19.1

Released 2023-09-30

- Remove `QUART_ENV` and env usage.

## Version 0.19.0

Released 2023-09-30

- Remove Flask-Patch. It has been replaced with the Quart-Flask-Patch extension.
- Remove references to first request, as per Flask.
- Await the background tasks before calling the after serving functions.
- Don't copy the app context into the background task.
- Allow background tasks a grace period to complete during shutdown.
- Base Quart on Flask, utilising Flask code where possible. This introduces a
  dependency on Flask.
- Fix trailing slash issue in URL concatenation for empty `path`.
- Use only CR in SSE documentation.
- Fix typing for websocket to accept auth data.
- Ensure subdomains apply to nested blueprints.
- Ensure `make_response` errors if the value is incorrect.
- Fix propagated exception handling.
- Ensure exceptions propagate before logging.
- Cope with `scope` extension value being `None`.
- Ensure the conditional 304 response is empty.
- Handle empty path in URL concatenation.
- Corrected typing hint for `abort` method.
- Fix `root_path` usage.
- Fix Werkzeug deprecation warnings.
- Add `.svg` to Jinja's autoescaping.
- Improve the `WebsocketResponse` error, by including the response.
- Add a file `mode` parameter to the `config.from_file` method.
- Show the subdomain or host in the `routes` command output.
- Upgrade to Blinker 1.6.
- Require Werkzeug 3.0.0 and Flask 3.0.0.
- Use `tomllib` rather than `toml`.

## Version 0.18.4

Released 2023-04-09

- Restrict Blinker to < 1.6 for 0.18.x versions to ensure it works with Quart's
  implementation.

## Version 0.18.3

Released 2022-10-08

- Corrected `quart.json.loads` type annotation.
- Fix signal handling on Windows.
- Add missing globals to Flask-Patch.

## Version 0.18.2

Released 2022-10-04

- Use `add_signal_handler` not `signal.signal`.

## Version 0.18.1

Released 2022-10-03

- Fix static hosting with resource path escaping the root.
- Adopt the Werkzeug/Flask `make_conditional` API/functionality.
- Restore the reloader to Quart.
- Support subdomains when testing.
- Fix the signal handling to work on Windows.

## Version 0.18.0

Released 2022-07-23

- Remove Quart's `safe_join`, use Werkzeug's version instead.
- Drop toml dependency, as it isn't required in Quart (use `config.from_file` as
  desired).
- Change `websocket.send_json` to match `jsonify`'s options.
- Allow while serving decorators on blueprints.
- Support synchronous background tasks, they will be run on a thread.
- Follow Flask's API and allow empty argument `Response` construction.
- Add `get_root_path` to helpers to match Flask.
- Support `silent` argument in `config.from_envvar`.
- Adopt Flask's logging setup.
- Add `stream_template` and `stream_template_string` functions to stream a large
  template in parts.
- Switch to Flask's top level name export style.
- Add `aborter` object to app to allow for `abort` customisation.
- Add `redirect` method to app to allow for `redirect` customisation.
- Remove usage of `LocalStacks`, using `ContextVars` more directly. This should
  improve performance, but introduces backwards incompatibility. `_*_ctx_stack`
  globals are removed, use `_context` instead. Extensions should store on
  `g` as appropriate. Requires Werkzeug >= 2.2.0.
- Returned lists are now jsonified.
- Move `url_for` to the app to allow for `url_for` customisation.
- Remove `config.from_json`, use `from_file` instead.
- Match the Flask views classes and API.
- Adopt the Flask cli code adding `--app`, `--env`, and `-debug` options to the
  CLI.
- Adopt the Flask JSON provider interface, use instead of JSON encoders and
  decoders.
- Switch to being a Pallets project.
- Requires at least Click version 8.

## Version 0.17.0

Released 2022-03-26

- Raise startup and shutdown errors.
- Allow loading of environment variables into the config.
- Switch to Werkzeug's `redirect`.
- Import `Markup` and `escape` from MarkupSafe.

## Version 0.16.3

Released 2022-02-02

- Ensure auth is sent on test client requests.

## Version 0.16.2

Released 2021-12-14

- Await background task shutdown after shutdown functions.
- Use the before websocket not request functions.

## Version 0.16.1

Released 2021-11-17

- Add missing serving exception handling.

## Version 0.16.0

Released 2021-11-09

- Support an `auth` argument in the test client.
- Support Python 3.10.
- Utilise `ensure_async` in the copy context functions.
- Add support for background tasks via `app.add_background_task`.
- Give a clearer error for invalid response types.
- Make `open_resource` and `open_instance_resource` async.
- Allow `save_session` to accept None as a response value.
- Rename errors to have an `Error` suffix.
- Fix typing of before (first) request callables.
- Support view sync handlers.
- Fix import of method `redirect` from Flask.
- Fix registering a blueprint twice with differing names.
- Support `ctx.pop()` without passing `exc` explicitly.
- A request timeout error should be raised on timeout.
- Remove Jinja warnings.
- Use the websocket context in the websocket method.
- Raise any lifespan startup failures when testing.
- Fix handler call order based on blueprint nesting.
- Allow for generators that yield strings to be used.
- Reorder acceptance to prevent race conditions.
- Prevent multiple task form body parsing via a lock.

## Version 0.15.1

Released 2021-05-24

- Improve the `g` `AppGlobals` typing.
- Fix nested blueprint `url_prefixes`.
- Ensure the session is created before url matching.
- Fix Flask Patch sync wrapping async.
- Don't try to parse the form data multiple times.
- Fix blueprint naming allowing blueprints to be registered with a
  different name.
- Fix teardown callable typing.

## Version 0.15.0

Released 2021-05-11

- Add the `quart routes` to output the routes in the app.
- Add the ability to close websocket connections with a reason if supported by
  the server.
- Revert `AppContext` lifespan interaction change in 0.14. It is not possible to
  introduce this and match Flask's `g` usage.
- Add syntactic sugar for route registration allowing `app.get`, `app.post`,
  etc. for app and blueprint instances.
- Support handlers returning a Werkzeug `Response`.
- Remove Quart's exceptions and use Werkzeug's. This may cause incompatibility
  to fix import from `werkzeug.exceptions` instead of `quart.exceptions`.
- Switch to Werkzeug's locals and Sans-IO wrappers.
- Allow for files to be sent via test client, via a `files` argument.
- Make the `NoAppException` clearer.
- Support nested blueprints.
- Support `while_serving` functionality.
- Correct routing host case matching.
- Cache flashed message on `request.flashes`.
- Fix debug defaults and overrides using `run`.
- Adopt Werkzeug's timestamp parsing.
- Only show the traceback response if propagating exceptions.
- Fix unhandled exception handling.
- Support `url_for` in websocket contexts.
- Fix cookie jar handling in test client.
- Support `SERVER_NAME` configuration for the `run` method.
- Correctly support `root_paths`.
- Support str and bytes streamed responses.
- Match Flask and consume the raw data when form parsing.

## Version 0.14.1

Released 2020-12-13

- Add missing receive to test request connection and docs.
- Add the `templates_auto_reload` API.
- Setting the `debug` property on the app now also sets the auto reloading for
  the Jinja environment.

## Version 0.14.0

Released 2020-12-05

- Add `user_agent` property to requests/websockets to easily extract the user
  agent using Werkzeug's `UserAgent` class.
- Set the content length when using send file instead of using chunked
  transfer encoding.
- Introduce a `test_app` method, this should be used to ensure that the startup
  & shutdown functions are run during testing.
- Prevent local data sharing.
- Officially support Python 3.9.
- Add send and receive json to the test websocket client, allows a simpler way
  for json to be sent and received using the app's encoder and decoder.
- Add signals for websocket message receipt and sending, specifically the
  `websocket_received` and `websocket_sent` signals.
- Add `dump` and `load` functions to the json module, as matching Flask.
- Enhance the dev server output.
- Change `AppContext` lifespan interaction - this pushes the app context on
  startup and pops on shutdown meaning `g` is available throughout without being
  cleared.
- Major refactor of the testing system - this ensures that any middleware and
  lifespans are correctly tested. It also introduces a`request` method on the
  test client for a request connection (like the websocket connection) for
  testing streaming.

## Version 0.13.1

Released 2020-09-09

- Add the `data` property to the patched request attributes.
- Fix WebSocket ASGI rejection (for servers that don't support the ASGI
  WebSocket response extension).
- Don't wrap commands in `with_appcontext` by default.
- Fix CSP parsing for the report-only header.
- Wait for tasks to complete when cancelled.
- Clean up the generator when the response exits.
- Fix request data handling with Flask-Patch.

## Version 0.13.0

Released 2020-07-14

- Set cookies from the testing jar for websockets.
- Restore Flask-Patch sync handling to pre 0.11. This means that sync route
  handlers, before request, and more, are **not** run in a thread if Flask-Patch
  is used. This restores Flask-SQLAlchemy support (with Flask-Patch).
- Accept additional attributes to the delete cookie.

## Version 0.12.0

Released 2020-05-21

- Add `certfile` and `keyfile` arguments to cli.
- `Request.host` value returns an empty string rather than `None` for HTTP/1.0
  requests without a `Host` header.
- Fix type of query string argument to Werkzeug `Map` fixing a `TypeError`.
- Add ASGI `scope` dictionary to `request`.
- Ensure that `FlaskGroup` exists when using `flask_patch` by patching the
  `flask.cli` module from quart.
- Add `quart.cli.with_appcontext` matching the Flask API.
- Make `quart.Blueprint` registration compatible with `flask.Blueprint`.
- Make the `add_url_rule` API match the Flask API.
- Resolve error handlers by most specific first (matches Flask).
- Support test sessions and context preservation when testing.
- Add `lookup_app` and `lookup_request` to Flask patch globals.
- Make `quart.Blueprint` constructor fully compatible with `flask.Blueprint`.
- Ensure url defaults aren't copied between blueprint routes.

## Version 0.11.5

Released 2020-03-31

- Ensure any exceptions are raised in the ASGI handling code.
- Support url defaults in the blueprint API.

## Version 0.11.4

Released 2020-03-29

- Add a testing patch to ensure `FlaskClient` exists.
- Security fix for the `htmlsafe` function.
- Default to the map's strict slashes setting.
- Fix host normalisation for route matching.
- Add subdomain to the blueprint API.

## Version 0.11.3

Released 2020-02-26

- Lowercase header names passed to cgi `FieldStorage`.

## Version 0.11.2

Released 2020-02-10

- Fix debug traceback rendering.
- Fix `multipart/form-data` parsing.
- Uncomment cookie parameters.
- Add `await` to the `LocalProxy` mappings.

## Version 0.11.1

Released 2020-02-09

- Fix cors header accessors and setters.
- Fix `iscoroutinefunction` with Python3.7.
- Fix `after_request`/`_websocket` function typing.

## Version 0.11.0

Released 2020-02-08

*This contains all the bug fixes from the 0.6 branch.*

- Allow relative `root_path` values.
- Add a `TooManyRequests`, 429, exception.
- Run synchronous code via a `ThreadPoolExecutor`. This means that sync route
  handlers, before request, and more, are run in a thread.
  **This is a major change.**
- Add an `asgi_app` method for middleware usage, for example
  `quart_app.asgi_app = Middleware(quart_app.asgi_app)`.
- Add a `run_sync` function to run synchronous code in a thread pool with the
  Quart contexts present.
- Set cookies on redirects when testing.
- Follow the Flask API for `dumps`/`loads`.
- Support loading configuration with a custom loader, `from_file` this allows
  for toml format configurations (among others).
- Match the Werkzeug API in `redirect`.
- Respect `QUART_DEBUG` when using `quart run`.
- Follow the Flask exception propagation rules, ensuring exceptions
  are propagated in testing.
- Support Python 3.8.
- Redirect with a 308 rather than 301 (following Flask/Werkzeug).
- Add a `_QUART_PATCHED` marker to all patched modules.
- Ensure multiple cookies are respected during testing.
- Switch to Werkzeug for datastructures and header parsing and dumping.
  **This is a major change.**
- Make the lock class customisable by the app subclass, this allows Quart-Trio
  to override the lock type.
- Add a `run_task` method to `Quart` (app) class. This is a task based on the
  `run` method assumptions that can be awaited or run as desired.
- Switch JSON tag datetime format to allow reading of Flask encoded tags.
- Switch to Werkzeug's cookie code. **This is a major change.**
- Switch to Werkzeug's routing code. **This is a major change.**
- Add signal handling to `run` method, but not the `run_task` method.

## Version 0.6.15

Released 2019-10-17

**This is the final 0.6 release and the final release to support Python3.6,
Python3.8 is now available.**

- Handle `http.request` without a `body` key

## Version 0.10.0

Released 2019-08-30

*This contains all the bug fixes from the 0.6 branch.*

- Support aborting with a `Response` argument.
- Fix JSON type hints to match typeshed.
- Update to Hypercorn 0.7.0 as minimum version.
- Ensure the default response timeout is set.
- Allow returning dictionaries from view functions, this follows a new addition
  to Flask.
- Ensure the response timeout has a default.
- Correct testing websocket typing.
- Accept `json`, `data`, or `form` arguments to `test_request_context`.
- Support `send_file` sending a `BytesIO` object.
- Add `samesite` cookie support (requires Python 3.8).
- Add a `ContentSecurityPolicy` datastructure, this follows a new addition to
  Werkzeug.
- Unblock logging I/O by logging in separate threads.
- Support ASGI `root_path` as a prepended path to all routes.

## Version 0.6.14

Released 2019-08-30

- Follow Werkzeug `LocalProxy` name API.
- Ensure multiple files are correctly loaded.
- Ensure `make_response` status code is an int.
- Be clear about header encoding.
- Ensure loading form/files data is timeout protected.
- Add missing `Unauthorized`, `Forbidden`, and `NotAcceptable` exception
  classes.

## Version 0.9.1

Released 2019-05-12

- Unquote the path in the test client, following the ASGI standard.
- Follow Werkzeug `LocalProxy` name API.
- Ensure multiple files are correctly loaded.

## Version 0.9.0

Released 2019-04-22

*This contains all the bug fixes from the 0.6 and 0.8 branches.*

- Highlight the traceback line of code when using the debug system.
- Ensure `debug` has an effect when passed to `app.run`.
- Change the `test_request_context` arguments to match the test client `open`
  arguments.
- Fix form data loading limit type.
- Support async Session Interfaces (with continued support for sync interfaces).
- Added `before_app_websocket`, and `after_app_websocket` methods to
  `Blueprint`.
- Support sending headers on WebSocket acceptance (this requires ASGI server
  support, the default Hypercorn supports this).
- Support async teardown functions (with continued support for sync functions).
- Match the Flask API argument order for `send_file` adding a `mimetype`
  argument and supporting attachment sending.
- Make the requested subprotocols available via the websocket class,
  `websocket.requested_subprotocols`.
- Support session saving with WebSockets (errors for cookie sessions if the
  WebSocket connection has been accepted).
- Switch to be an ASGI 3 framework (this requires ASGI server support, the
  default Hypercorn supports this).
- Refactor push promise API, removes the `response.push_promises` attribute.
- Accept `Path` types throughout and switch to `Path` types internally.

## Version 0.6.13

Released 2019-04-22

- Fix multipart parsing.
- Added `Map.iter_rules(endpoint)` method.
- Cope if there is no source code when using the debug system.

## Version 0.8.1

Released 2019-02-09

- Make the `safe_join` function stricter.
- Parse `multipart/form-data` correctly.
- Add missing `await`.

## Version 0.8.0

Released 2019-01-29

*This contains all the bug fixes from the 0.6 and 0.7 branches.*

- Raise an error if the loaded app is not a Quart instance.
- Remove unused `AccessLogAtoms`.
- Change the `Quart.run` method interface, this reduces the available options
  for simplicity. See hypercorn for an extended set of deployment configuration.
- Utilise the Hypercorn `serve` function, requires Hypercorn >= 0.5.0.
- Added `list_templates` method to `DispatchingJinjaLoader`.
- Add additional methods to the `Accept` datastructure, specifically keyed
  accessors.
- Expand the `abort` functionality and signature, to allow for the `description`
  and `name` to be optionally specified.
- Add a `make_push_promise` function, to allow for push promises to be sent at
  any time during the request handling e.g. pre-emptive pushes.
- Rethink the Response Body structure to allow for more efficient handling of
  file bodies and the ability to extend how files are managed (for Quart-Trio
  and others).
- Add the ability to send conditional 206 responses. Optionally, a response can
  be made conditional by awaiting the `make_conditional` method with an argument
  of the request range.
- Recommend Mangum for serverless deployments.
- Added `instance_path` and `instance_relative_config` to allow for an instance
  folder to be used.

## Version 0.6.12

Released 2019-01-29

- Raise a `BadRequest` if the body encoding is wrong.
- Limit Hypercorn to versions < 0.6.
- Fix matching of `MIMEAccept` values.
- Handle the special routing case of `/`.
- Ensure sync functions work with async signals.
- Ensure redirect location headers are full URLs.
- Ensure open-ended `Range` header works.
- Ensure `RequestEntityTooLarge` errors are correctly raised.

## Version 0.7.2

Released 2019-01-03

- Fix the url display bug.
- Avoid crash in `flask_patch` isinstance.
- Cope with absolute paths sent in the scope.

## Version 0.7.1

Released 2018-12-18

- Fix Flask patching step definition.

## Version 0.7.0

Released 2018-12-16

- Support only Python 3.7, see the 0.6.X releases for continued Python
  3.6 support.
- Introduce `ContextVar` for local storage.
- Change default redirect status code to 302.
- Support integer/float cookie expires.
- Specify cookie date format (differs to Flask).
- Remove the Gunicorn workers, please use a ASGI server instead.
- Remove Gunicorn compatibility.
- Introduce a `Headers` data structure.
- Implement `follow_redirects` in Quart test client.
- Adopt the ASGI lifespan protocol.

## Version 0.6.11

Released 2018-12-09

- Support static files in blueprints.
- Ensure automatic options API matches Flask and works.
- Fix `app.run` SSL usage and Hypercorn compatibility.

## Version 0.6.10

Released 2018-11-12

- Fix async body iteration cleanup.

## Version 0.6.9

Released 2018-11-10

- Fix async body iteration deadlock.
- Fix ASGI handling to ensure completion.

## Version 0.6.8

Released 2018-10-21

- Ensure an event loop is specified on `app.run`.
- Ensure handler responses are finalized.
- Ensure the ASGI callable returns on completion.

## Version 0.6.7

Released 2018-09-23

- Fix ASGI conversion of websocket data (str or bytes).
- Ensure redirect url includes host when host matching.
- Ensure query strings are present in redirect urls.
- Ensure header values are string types.
- Fix incorrect endpoint override error for synchronous view functions.

## Version 0.6.6

Released 2018-08-27

- Add type conversion to `getlist` (on multidicts)
- Correct ASGI client usage (allows for `None`)
- Ensure overlapping requests work without destroying the other contexts.
- Ensure only integer status codes are accepted.

## Version 0.6.5

Released 2018-08-05

- Change default redirect status code to 302.
- Support query string parsing from test client paths.
- Support int/float cookie expires values.
- Correct the cookie date format to RFC 822.
- Copy `sys.modules` to prevent dictionary changed errors.
- Ensure request body iteration returns all data.
- Set `Host` header (if missing) for HTTP/1.0.
- Set the correct defaults for `_external` in `url_for`.

## Version 0.6.4

Released 2018-07-15

- Correctly handle request query strings.
- Restore log output when running in development mode.
- Allow for multiple query string values when building urls, e.g. `a=1&a=2`.
- Ensure the Flask Patch system works with Python 3.7.

## Version 0.6.3

Released 2018-07-05

- Ensure compatibility with Python 3.7

## Version 0.6.2

Released 2018-06-24

- Remove class member patching from flask-patch system, as it was unreliable.
- Ensure ASGI websocket handler closes on disconnect.
- Cope with optional client values in ASGI scope.

## Version 0.6.1

Released 2018-06-18

- Accept `PathLike` objects to the `send_file` function.
- Fix mutable methods in blueprint routes or url rule addition.
- Don't lowercase header values.
- Support automatic options on `View` classes.

## Version 0.6.0

Released 2018-06-11

- Quart is now an ASGI framework, and requires an ASGI server to serve requests.
  [Hypercorn](https://github.com/pgjones/hypercorn) is used in development and
  is recommended for production. Hypercorn is a continuation of the Quart
  serving code.
- Add before and after serving functionality, this is provisional.
- Add caching, last modified and etag information to static files served via
  `send_file`.
- Fix date formatting in response headers.
- `make_response` should error if response is `None`.
- Deprecate the Gunicorn workers, see ASGI servers (e.g. Uvicorn).
- Ensure shell context processors work.
- Change template context processors to be async, this is backwards
  incompatible.
- Change websocket API to be async, this is backwards incompatible.
- Allow the websocket class to be configurable by users.
- Catch signals on Windows.
- Preserve context in Flask-Patch system.
- Add the websocket API to blueprints.
- Add host, subdomain, and default options to websocket routes.
- Support `defaults` on `route` or `add_url_rule` usage.
- Introduce a more useful `BuildError`
- Match Flask after request function execution order.
- Support `required_methods` on view functions.
- Added CORS, Access Control, datastructures to request and response objects.
- Allow type conversion in (CI)MultiDict get.

## Version 0.5.0

Released 2018-04-13

- Further API compatibility with Flask, specifically submodules, wrappers, and
  the app.
- Ensure error handlers work.
- Await `get_data` in Flask Patch system.
- Fix rule building, specifically additional arguments as query strings.
- Ability to add defaults to routes on definition.
- Allow set_cookie to accept bytes arguments.
- Ensure mimetype are returned.
- Add host matching, and subdomains for routes.
- Introduce implicit sequence conversion to response data.
- URL and host information on requests.
- Add a debug page, which shows tracebacks on errors.
- Fix accept header parsing.
- Cope with multi lists in forms.
- Add cache control, etag and range header structures.
- Add host, url, scheme and path correctly to path wrappers.
- Fix CLI module parsing.
- Add auto reloading on file changes.
- Ignore invalid upgrade headers.
- Fix h2c requests when there is a body (to not upgrade).
- Refactor of websocket API, matching the request API as an analogue.
- Refactor to mitigate DOS attacks, add documentation section.
- Allow event loop to be specified when running apps.
- Ensure automatic options work.
- Rename `TestClient` -> `QuartClient` to match Flask naming.

## Version 0.4.1

Released 2018-01-27

- Fix HTTP/2 support and pass h2spec compliance testing.
- Fix Websocket support and pass autobahn fuzzy test compliance testing.
- Fix HEAD request support (don't try to send a body).
- Fix content-type (remove forced override).

## Version 0.4.0

Released 2018-01-14

- Change to async signals and context management. This allows the signal
  receivers to be async (which is much more useful) but requires changes to any
  current usage (notably test contexts).
- Add initial support of websockets.
- Support HTTP/1.1 to HTTP/2 (h2c) upgrades, includes supporting HTTP/2 without
  SSL (note browsers don't support this).
- Add timing to access logging.
- Add a new logo :) thanks to @koddr.
- Support streaming of the request body.
- Add initial CLI support, using click.
- Add context copying helper functions and clarify how to stream a response.
- Improved tutorials.
- Allow the request to be limited to prevent DOS attacks.

## Version 0.3.1

Released 2017-10-25

- Fix incorrect error message for HTTP/1.1 requests.
- Fix HTTP/1.1 pipelining support and error handling.

## Version 0.3.0

Released 2017-10-10

- Change `flask_ext` name to `flask_patch` to clarify that it is not the
  pre-existing `flask_ext` system and that it patches Quart to provide
  Flask imports.
- Added support for views.
- Match Werkzeug API for FileStorage.
- Support HTTP/2 pipelining.
- Add access logging.
- Add HTTP/2 Server push, see the `push_promises` set on a `Response` object.
- Add idle timeouts.

## Version 0.2.0

Released 2017-07-22

*This is still an alpha version of Quart.*

- Support for Flask extensions via the `flask_ext` module (if imported).
- Initial documentation setup and actual documentation including API docstrings.
- Closer match to the Flask API, most modules now match the Flask public API.

## Version 0.1.0

Released 2017-05-21

- Released initial pre alpha version.
