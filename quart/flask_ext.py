# This adds a 'fake' set of Flask modules for Flask extensions to use,
# these 'fake' modules however point at the equivalent Quart modules
# apart from the request proxy, which has an additional syncrhonous
# layer. This should allow most Flask extensions to work, however it
# also degrades performance and hence is a trade off.

import sys
from functools import partial
from importlib.util import find_spec, module_from_spec

from multidict import MultiDict

from .globals import _request_ctx_lookup
from .local import LocalProxy


class FlaskRequest(LocalProxy):

    @property
    def form(self) -> MultiDict:
        return self._get_current_object()._form

    @property
    def files(self) -> MultiDict:
        return self._get_current_object()._files


if 'flask' in sys.modules:
    raise ImportError('Cannot mock flask, already imported')

spec = find_spec('quart')
flask_module = module_from_spec(spec)
spec.loader.exec_module(flask_module)
flask_module.Flask = flask_module.Quart  # type: ignore
flask_request = FlaskRequest(partial(_request_ctx_lookup, 'request'))  # type: ignore
flask_module.request = flask_request  # type: ignore
del flask_module.Quart  # type: ignore

flask_modules = {'flask': flask_module}
for name, module in sys.modules.items():
    if name.startswith('quart.'):
        flask_modules[name.replace('quart.', 'flask.')] = module

flask_modules['flask.globals'].request = flask_request  # type: ignore
sys.modules.update(flask_modules)

quart_handle_request = sys.modules['flask.app'].Quart.handle_request


async def new_handle_request(self, request):  # type: ignore
    await request.form
    return await quart_handle_request(self, request)


sys.modules['flask.app'].Quart.handle_request = new_handle_request
