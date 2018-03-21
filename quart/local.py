import asyncio
import copy
from collections import defaultdict
from typing import Any, Callable, Dict


class TaskLocal:
    """An object local to the current task."""

    __slots__ = ('_storage',)

    def __init__(self) -> None:
        # Note as __setattr__ is overidden below, use the object __setattr__
        object.__setattr__(self, '_storage', defaultdict(dict))

    def __getattr__(self, name: str) -> Any:
        try:
            return self._storage[TaskLocal._task_identity()][name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self._storage[TaskLocal._task_identity()][name] = value

    def __delattr__(self, name: str) -> None:
        try:
            del self._storage[TaskLocal._task_identity()][name]
        except KeyError:
            raise AttributeError(name)

    @staticmethod
    def _task_identity() -> int:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.Task.current_task()
            task_id = id(task)
            return task_id
        else:
            return 0


class LocalStack:

    def __init__(self) -> None:
        self._task_local = TaskLocal()

    def push(self, value: Any) -> None:
        stack = getattr(self._task_local, 'stack', None)
        if stack is None:
            self._task_local.stack = stack = []  # type: ignore
        stack.append(value)

    def pop(self) -> Any:
        stack = getattr(self._task_local, 'stack', None)
        if stack is None or stack == []:
            return None
        else:
            return stack.pop()

    @property
    def top(self) -> Any:
        try:
            return self._task_local.stack[-1]
        except (AttributeError, IndexError):
            return None


class LocalProxy:
    """Proxy to a task local object."""
    __slots__ = ('__dict__', '__local', '__wrapped__')

    def __init__(self, local: Callable) -> None:
        # Note as __setattr__ is overidden below, use the object __setattr__
        object.__setattr__(self, '__LocalProxy_local', local)
        object.__setattr__(self, '__wrapped__', local)

    def _get_current_object(self) -> Any:
        return object.__getattribute__(self, '__LocalProxy_local')()

    @property
    def __dict__(self) -> Dict[str, Any]:  # type: ignore
        try:
            return self._get_current_object().__dict__
        except RuntimeError:
            raise AttributeError('__dict__')

    def __repr__(self) -> str:
        try:
            obj = self._get_current_object()
        except RuntimeError:
            return '<%s unbound>' % self.__class__.__name__
        return repr(obj)

    def __bool__(self) -> bool:
        try:
            return bool(self._get_current_object())
        except RuntimeError:
            return False

    def __dir__(self) -> Any:
        try:
            return dir(self._get_current_object())
        except RuntimeError:
            return []

    def __getattr__(self, name: Any) -> Any:
        if name == '__members__':
            return dir(self._get_current_object())
        return getattr(self._get_current_object(), name)

    def __setitem__(self, key: Any, value: Any) -> Any:
        self._get_current_object()[key] = value

    def __delitem__(self, key: Any) -> Any:
        del self._get_current_object()[key]

    async def __aiter__(self) -> Any:
        async for x in self._get_current_object():
            yield x

    __setattr__ = lambda x, n, v: setattr(x._get_current_object(), n, v)  # type: ignore # noqa
    __delattr__ = lambda x, n: delattr(x._get_current_object(), n)  # type: ignore # noqa
    __str__ = lambda x: str(x._get_current_object())  # type: ignore # noqa
    __lt__ = lambda x, o: x._get_current_object() < o  # type: ignore # noqa
    __le__ = lambda x, o: x._get_current_object() <= o  # type: ignore # noqa
    __eq__ = lambda x, o: x._get_current_object() == o  # type: ignore # noqa
    __ne__ = lambda x, o: x._get_current_object() != o  # type: ignore # noqa
    __gt__ = lambda x, o: x._get_current_object() > o  # type: ignore # noqa
    __ge__ = lambda x, o: x._get_current_object() >= o  # type: ignore # noqa
    __hash__ = lambda x: hash(x._get_current_object())  # type: ignore # noqa
    __call__ = lambda x, *a, **kw: x._get_current_object()(*a, **kw)  # type: ignore # noqa
    __len__ = lambda x: len(x._get_current_object())  # type: ignore # noqa
    __getitem__ = lambda x, i: x._get_current_object()[i]  # type: ignore # noqa
    __iter__ = lambda x: iter(x._get_current_object())  # type: ignore # noqa
    __contains__ = lambda x, i: i in x._get_current_object()  # type: ignore # noqa
    __add__ = lambda x, o: x._get_current_object() + o  # type: ignore # noqa
    __sub__ = lambda x, o: x._get_current_object() - o  # type: ignore # noqa
    __mul__ = lambda x, o: x._get_current_object() * o  # type: ignore # noqa
    __floordiv__ = lambda x, o: x._get_current_object() // o  # type: ignore # noqa
    __mod__ = lambda x, o: x._get_current_object() % o  # type: ignore # noqa
    __divmod__ = lambda x, o: x._get_current_object().__divmod__(o)  # type: ignore # noqa
    __pow__ = lambda x, o: x._get_current_object() ** o  # type: ignore # noqa
    __lshift__ = lambda x, o: x._get_current_object() << o  # type: ignore # noqa
    __rshift__ = lambda x, o: x._get_current_object() >> o  # type: ignore # noqa
    __and__ = lambda x, o: x._get_current_object() & o  # type: ignore # noqa
    __xor__ = lambda x, o: x._get_current_object() ^ o  # type: ignore # noqa
    __or__ = lambda x, o: x._get_current_object() | o  # type: ignore # noqa
    __div__ = lambda x, o: x._get_current_object().__div__(o)  # type: ignore # noqa
    __truediv__ = lambda x, o: x._get_current_object().__truediv__(o)  # type: ignore # noqa
    __neg__ = lambda x: -(x._get_current_object())  # type: ignore # noqa
    __pos__ = lambda x: +(x._get_current_object())  # type: ignore # noqa
    __abs__ = lambda x: abs(x._get_current_object())  # type: ignore # noqa
    __invert__ = lambda x: ~(x._get_current_object())  # type: ignore # noqa
    __complex__ = lambda x: complex(x._get_current_object())  # type: ignore # noqa
    __int__ = lambda x: int(x._get_current_object())  # type: ignore # noqa
    __float__ = lambda x: float(x._get_current_object())  # type: ignore # noqa
    __oct__ = lambda x: oct(x._get_current_object())  # type: ignore # noqa
    __hex__ = lambda x: hex(x._get_current_object())  # type: ignore # noqa
    __index__ = lambda x: x._get_current_object().__index__()  # type: ignore # noqa
    __coerce__ = lambda x, o: x._get_current_object().__coerce__(x, o)  # type: ignore # noqa
    __enter__ = lambda x: x._get_current_object().__enter__()  # type: ignore # noqa
    __exit__ = lambda x, *a, **kw: x._get_current_object().__exit__(*a, **kw)  # type: ignore # noqa
    __radd__ = lambda x, o: o + x._get_current_object()  # type: ignore # noqa
    __rsub__ = lambda x, o: o - x._get_current_object()  # type: ignore # noqa
    __rmul__ = lambda x, o: o * x._get_current_object()  # type: ignore # noqa
    __rdiv__ = lambda x, o: o / x._get_current_object()  # type: ignore # noqa
    __rtruediv__ = __rdiv__  # type: ignore # noqa
    __rfloordiv__ = lambda x, o: o // x._get_current_object()  # type: ignore # noqa
    __rmod__ = lambda x, o: o % x._get_current_object()  # type: ignore # noqa
    __rdivmod__ = lambda x, o: x._get_current_object().__rdivmod__(o)  # type: ignore # noqa
    __copy__ = lambda x: copy.copy(x._get_current_object())  # type: ignore # noqa
    __deepcopy__ = lambda x, memo: copy.deepcopy(x._get_current_object(), memo)  # type: ignore # noqa
