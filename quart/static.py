import mimetypes
import os
import pkgutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import AnyStr, Optional, Union
from typing.io import IO
from zlib import adler32

from aiofiles import open as async_open
from jinja2 import FileSystemLoader

from .exceptions import NotFound
from .globals import current_app
from .wrappers import Response

DEFAULT_MIMETYPE = 'application/octet-stream'
FilePath = Union[AnyStr, os.PathLike]


class PackageStatic:

    def __init__(
            self,
            import_name: str,
            template_folder: Optional[str]=None,
            root_path: Optional[str]=None,
    ) -> None:
        self.import_name = import_name
        self.template_folder = template_folder

        self.root_path = self._find_root_path(root_path)

        self._static_folder: Optional[str] = None
        self._static_url_path: Optional[str] = None

    @property
    def static_folder(self) -> Optional[str]:
        if self._static_folder is not None:
            return os.path.join(self.root_path, self._static_folder)
        else:
            return None

    @static_folder.setter
    def static_folder(self, static_folder: str) -> None:
        self._static_folder = static_folder

    @property
    def static_url_path(self) -> Optional[str]:
        if self._static_url_path is not None:
            return self._static_url_path
        if self.static_folder is not None:
            return '/' + os.path.basename(self.static_folder)
        else:
            return None

    @static_url_path.setter
    def static_url_path(self, static_url_path: str) -> None:
        self._static_url_path = static_url_path

    @property
    def has_static_folder(self) -> bool:
        return self.static_folder is not None

    @property
    def jinja_loader(self) -> Optional[FileSystemLoader]:
        if self.template_folder is not None:
            return FileSystemLoader(
                os.path.join(self.root_path, self.template_folder),
            )
        else:
            return None

    def get_send_file_max_age(self, filename: str) -> int:
        return current_app.send_file_max_age_default.total_seconds()

    async def send_static_file(self, filename: str) -> Response:
        if not self.has_static_folder:
            raise RuntimeError('No static folder for this object')
        return await send_from_directory(self.static_folder, filename)

    def open_resource(self, path: str, mode: str='rb') -> IO[AnyStr]:
        """Open a file for reading.

        Use as

        .. code-block:: python

            with app.open_resouce(path) as file_:
                file_.read()
        """
        if mode not in {'r', 'rb'}:
            raise ValueError('Files can only be opened for reading')
        return open(os.path.join(self.root_path, path), mode)

    def _find_root_path(self, root_path: Optional[str]=None) -> str:
        if root_path is not None:
            return root_path
        else:
            module = sys.modules.get(self.import_name)
            if module is not None and hasattr(module, '__file__'):
                file_path = module.__file__
            else:
                loader = pkgutil.get_loader(self.import_name)
                if loader is None or self.import_name == '__main__':
                    return os.getcwd()
                else:
                    file_path = loader.get_filename(self.import_name)  # type: ignore
            return os.path.dirname(os.path.abspath(file_path))


def safe_join(directory: str, *paths: str) -> Path:
    """Safely join the paths to the known directory to return a full path.

    Raises:
        NotFound: if the full path does not share a commonprefix with
        the directory.
    """
    safe_path = Path(directory).resolve()
    full_path = Path(directory, *paths).resolve()
    if not str(full_path).startswith(str(safe_path)):
        raise NotFound()
    return full_path


async def send_from_directory(directory: str, file_name: str) -> Response:
    file_path = safe_join(directory, file_name)
    if not os.path.isfile(file_path):
        raise NotFound()
    return await send_file(file_path)  # type: ignore


async def send_file(
        filename: FilePath,
        add_etags: bool=True,
        cache_timeout: Optional[int]=None,
        last_modified: Optional[datetime]=None,
) -> Response:
    """Return a Reponse to send the filename given.

    Arguments:
        filename: The filename (path) to send, remember to use
            :func:`safe_join`.
        add_etags: Set etags based on the filename, size and
            modification time.
        cache_timeout: Time in seconds for the response to be cached.
        last_modified: Used to override the last modified value.

    """
    file_path = os.fspath(filename)
    mimetype = mimetypes.guess_type(os.path.basename(file_path))[0] or DEFAULT_MIMETYPE
    async with async_open(file_path, mode='rb') as file_:
        data = await file_.read()
    response = current_app.response_class(data, mimetype=mimetype)

    if last_modified is not None:
        response.last_modified = last_modified
    else:
        response.last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))

    response.cache_control.public = True
    cache_timeout = cache_timeout or current_app.get_send_file_max_age(file_path)
    if cache_timeout is not None:
        response.cache_control.max_age = cache_timeout
        response.expires = datetime.utcnow() + timedelta(seconds=cache_timeout)

    if add_etags:
        file_tag = file_path.encode('utf-8') if isinstance(file_path, str) else file_path
        response.set_etag(
            '{}-{}-{}'.format(
                os.path.getmtime(file_path), os.path.getsize(file_path),
                adler32(file_tag),
            ),
        )
    return response
