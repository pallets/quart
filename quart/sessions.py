import hashlib
import json
import uuid
from base64 import b64decode, b64encode
from collections.abc import MutableMapping
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional, TYPE_CHECKING

from itsdangerous import BadSignature, URLSafeTimedSerializer

from .wrappers import Request, Response

if TYPE_CHECKING:
    from .app import Quart  # noqa


class SessionMixin:
    """Use to extend a dict with Session attributes.

    The attributes add standard and expected Session modification flags.

    Attributes:
        modified: Indicates if the Session has been modified during
            the request handling.
        new: Indicates if the Session is new.
    """

    modified = True
    new = False

    @property
    def permanent(self) -> bool:
        return self.get('_permanent', False)  # type: ignore

    @permanent.setter
    def permanent(self, value: bool) -> None:
        self['_permanent'] = value  # type: ignore


def _wrap_modified(method: Callable) -> Callable:
    @wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        self.modified = True
        return method(self, *args, **kwargs)
    return wrapper


class Session(MutableMapping):
    """An abstract base class for Sessions."""
    pass


class SecureCookieSession(SessionMixin, dict, Session):
    """A session implementation using cookies.

    Note that the intention is for this session to use cookies, this
    class does not implement anything bar modification flags.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.modified = False

    __delitem__ = _wrap_modified(dict.__delitem__)
    __setitem__ = _wrap_modified(dict.__setitem__)
    clear = _wrap_modified(dict.clear)
    pop = _wrap_modified(dict.pop)
    popitem = _wrap_modified(dict.popitem)
    setdefault = _wrap_modified(dict.setdefault)
    update = _wrap_modified(dict.update)


def _wrap_no_modification(method: Callable) -> Callable:
    @wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError('Cannot create session, ensure there is a app secret key.')
    return wrapper


class NullSession(Session, dict):
    """A session implementation for sessions without storage."""

    __delitem__ = _wrap_no_modification(dict.__delitem__)
    __setitem__ = _wrap_no_modification(dict.__setitem__)
    clear = _wrap_no_modification(dict.clear)
    pop = _wrap_no_modification(dict.pop)
    popitem = _wrap_no_modification(dict.popitem)
    setdefault = _wrap_no_modification(dict.setdefault)
    update = _wrap_no_modification(dict.update)


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")


class TaggedJSONSerializer:
    """A itsdangerous compatible JSON serializer.

    This will add tags to the JSON output corresponding to the python
    type.
    """

    LOADS_MAP = {
        ' t': tuple,
        ' u': uuid.UUID,
        ' b': b64decode,
        # ' m': Markup,
        ' d': _parse_datetime,
    }

    def dumps(self, value: Any) -> str:
        return json.dumps(TaggedJSONSerializer._tag_type(value), separators=(',', ':'))

    @staticmethod
    def _tag_type(value: Any) -> Any:
        if isinstance(value, tuple):
            return {' t': [TaggedJSONSerializer._tag_type(x) for x in value]}
        elif isinstance(value, uuid.UUID):
            return {' u': value.hex}
        elif isinstance(value, bytes):
            return {' b': b64encode(value).decode('ascii')}
        # elif callable(getattr(value, '__html__', None)):
        #     return {' m': str(value.__html__())}
        elif isinstance(value, list):
            return [TaggedJSONSerializer._tag_type(element) for element in value]
        elif isinstance(value, datetime):
            return {' d': value.isoformat(timespec='microseconds')}  # type: ignore
        elif isinstance(value, dict):
            return {key: TaggedJSONSerializer._tag_type(val) for key, val in value.items()}
        elif isinstance(value, str):
            return value
        else:
            return value

    @staticmethod
    def _untag_type(object_: Any) -> Any:
        if len(object_) != 1:
            return object_
        key, value = next(iter(object_.items()))
        if key in TaggedJSONSerializer.LOADS_MAP:
            return TaggedJSONSerializer.LOADS_MAP[key](value)  # type: ignore
        else:
            return object_

    def loads(self, value: str) -> Any:
        return json.loads(value, object_hook=TaggedJSONSerializer._untag_type)


class SessionInterface:
    """Base class for session interfaces.

    Attributes:
        null_session_class: Storage class for null (no storage)
            sessions.
        pickle_based: Indicates if pickling is used for the session.
    """
    null_session_class = NullSession
    pickle_based = False

    def make_null_session(self, app: 'Quart') -> NullSession:
        return self.null_session_class()

    def is_null_session(self, instance: object) -> bool:
        return isinstance(instance, self.null_session_class)

    def get_cookie_domain(self, app: 'Quart') -> Optional[str]:
        if app.config['SESSION_COOKIE_DOMAIN'] is not None:
            return app.config['SESSION_COOKIE_DOMAIN']
        elif app.config['SERVER_NAME'] is not None:
            return '.' + app.config['SERVER_NAME'].rsplit(':', 1)[0]
        else:
            return None

    def get_cookie_path(self, app: 'Quart') -> str:
        return app.config['SESSION_COOKIE_PATH'] or app.config['APPLICATION_ROOT'] or '/'

    def get_cookie_httponly(self, app: 'Quart') -> bool:
        return app.config['SESSION_COOKIE_HTTPONLY']

    def get_cookie_secure(self, app: 'Quart') -> bool:
        return app.config['SESSION_COOKIE_SECURE']

    def get_expiration_time(self, app: 'Quart', session: SessionMixin) -> Optional[datetime]:
        if session.permanent:
            return datetime.utcnow() + app.permanent_session_lifetime
        else:
            return None

    def should_set_cookie(self, app: 'Quart', session: SessionMixin) -> bool:
        if session.modified:
            return True
        save_each = app.config['SESSION_REFRESH_EACH_REQUEST']
        return save_each and session.permanent

    def open_session(self, app: 'Quart', request: Request) -> Optional[Session]:
        """Open an existing session from the request or create one.

        Returns:
            The Session object or None if no session can be created,
            in which case the :attr:`null_session_class` is expected
            to be used.
        """
        raise NotImplementedError()

    def save_session(self, app: 'Quart', session: Session, response: Response) -> Response:
        """Save the session argument to the response.

        Returns:
            The modified response, with the session stored.
        """
        raise NotImplementedError()


class SecureCookieSessionInterface(SessionInterface):

    digest_method = staticmethod(hashlib.sha1)  # type: ignore
    key_derivation = 'hmac'
    salt = 'cookie-session'
    serializer = TaggedJSONSerializer()
    session_class = SecureCookieSession

    def get_signing_serializer(self, app: 'Quart') -> Optional[URLSafeTimedSerializer]:
        if not app.secret_key:
            return None

        options = {
            'key_derivation': self.key_derivation,
            'digest_method': self.digest_method,
        }
        return URLSafeTimedSerializer(
            app.secret_key, salt=self.salt, serializer=self.serializer, signer_kwargs=options,
        )

    def open_session(self, app: 'Quart', request: Request) -> Optional[SecureCookieSession]:
        """Open a secure cookie based session.

        This will return None if a signing serializer is not availabe,
        usually if the config SECRET_KEY is not set.
        """
        signer = self.get_signing_serializer(app)
        if signer is None:
            return None

        cookie = request.cookies.get(app.session_cookie_name)
        if cookie is None:
            return self.session_class()
        try:
            data = signer.loads(
                cookie.value, max_age=app.permanent_session_lifetime.total_seconds(),
            )
            return self.session_class(**data)
        except BadSignature:
            return self.session_class()

    def save_session(  # type: ignore
            self, app: 'Quart', session: SecureCookieSession, response: Response,
    ) -> Response:
        """Saves the session to the response in a secure cookie."""
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        if not session:
            if session.modified:
                response.delete_cookie(app.session_cookie_name, domain=domain, path=path)
            return response

        if not self.should_set_cookie(app, session):
            return response

        data = self.get_signing_serializer(app).dumps(dict(session))
        response.set_cookie(  # type: ignore
            app.session_cookie_name,
            data,
            expires=self.get_expiration_time(app, session),
            httponly=self.get_cookie_httponly(app),
            domain=domain,
            path=path,
            secure=self.get_cookie_secure(app),
        )
        return response
