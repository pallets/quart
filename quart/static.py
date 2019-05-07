import mimetypes
import os
import pkgutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import AnyStr, IO, Optional
from zlib import adler32

from jinja2 import FileSystemLoader

from .exceptions import NotFound
from .globals import current_app, request
from .typing import FilePath
from .utils import file_path_to_path
from .wrappers import Response

DEFAULT_MIMETYPE = 'application/octet-stream'


class PackageStatic:

    def __init__(
            self,
            import_name: str,
            template_folder: Optional[str]=None,
            root_path: Optional[str]=None,
            static_folder: Optional[str]=None,
            static_url_path: Optional[str]=None,
    ) -> None:
        self.import_name = import_name
        self.template_folder = Path(template_folder) if template_folder is not None else None

        self.root_path = self._find_root_path(root_path)

        self._static_folder: Optional[Path] = None
        self._static_url_path: Optional[str] = None
        self.static_folder = static_folder
        self.static_url_path = static_url_path

    @property
    def static_folder(self) -> Optional[Path]:
        if self._static_folder is not None:
            return self.root_path / self._static_folder
        else:
            return None

    @static_folder.setter
    def static_folder(self, static_folder: Optional[FilePath]) -> None:
        if static_folder is not None:
            self._static_folder = file_path_to_path(static_folder)
        else:
            self._static_folder = None

    @property
    def static_url_path(self) -> Optional[str]:
        if self._static_url_path is not None:
            return self._static_url_path
        if self.static_folder is not None:
            return '/' + self.static_folder.name
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
            return FileSystemLoader(os.fspath(self.root_path / self.template_folder))
        else:
            return None

    def get_send_file_max_age(self, filename: str) -> int:
        return current_app.send_file_max_age_default.total_seconds()

    async def send_static_file(self, filename: str) -> Response:
        if not self.has_static_folder:
            raise RuntimeError('No static folder for this object')
        return await send_from_directory(self.static_folder, filename)

    def open_resource(self, path: FilePath, mode: str='rb') -> IO[AnyStr]:
        """Open a file for reading.

        Use as

        .. code-block:: python

            with app.open_resouce(path) as file_:
                file_.read()
        """
        if mode not in {'r', 'rb'}:
            raise ValueError('Files can only be opened for reading')
        return open(self.root_path / file_path_to_path(path), mode)

    def _find_root_path(self, root_path: Optional[str]=None) -> Path:
        if root_path is not None:
            return Path(root_path)
        else:
            module = sys.modules.get(self.import_name)
            if module is not None and hasattr(module, '__file__'):
                file_path = module.__file__
            else:
                loader = pkgutil.get_loader(self.import_name)
                if loader is None or self.import_name == '__main__':
                    return Path.cwd()
                else:
                    file_path = loader.get_filename(self.import_name)  # type: ignore
            return Path(file_path).resolve().parent


def safe_join(directory: FilePath, *paths: FilePath) -> Path:
    """Safely join the paths to the known directory to return a full path.

    Raises:
        NotFound: if the full path does not share a commonprefix with
        the directory.
    """
    try:
        safe_path = file_path_to_path(directory).resolve(strict=True)
        full_path = file_path_to_path(directory, *paths).resolve(strict=True)
    except FileNotFoundError:
        raise NotFound()
    try:
        full_path.relative_to(safe_path)
    except ValueError:
        raise NotFound()
    return full_path


async def send_from_directory(
        directory: FilePath,
        file_name: str,
        *,
        mimetype: Optional[str]=None,
        as_attachment: bool=False,
        attachment_filename: Optional[str]=None,
        add_etags: bool=True,
        cache_timeout: Optional[int]=None,
        conditional: bool=True,
        last_modified: Optional[datetime]=None,
) -> Response:
    """Send a file from a given directory.

    Arguments:
       directory: Directory that when combined with file_name gives
           the file path.
       file_name: File name that when combined with directory gives
           the file path.

    See :func:`send_file` for the other arguments.
    """
    file_path = safe_join(directory, file_name)
    if not file_path.is_file():
        raise NotFound()
    return await send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=as_attachment,
        attachment_filename=attachment_filename,
        add_etags=add_etags,
        cache_timeout=cache_timeout,
        conditional=conditional,
        last_modified=last_modified,
    )


async def send_file(
        filename: FilePath,
        mimetype: Optional[str]=None,
        as_attachment: bool=False,
        attachment_filename: Optional[str]=None,
        add_etags: bool=True,
        cache_timeout: Optional[int]=None,
        conditional: bool=False,
        last_modified: Optional[datetime]=None,
) -> Response:
    """Return a Reponse to send the filename given.

    Arguments:
        filename: The filename (path) to send, remember to use
            :func:`safe_join`.
        mimetype: Mimetype to use, by default it will be guessed or
            revert to the DEFAULT_MIMETYPE.
        as_attachment: If true use the attachment filename in a
            Content-Disposition attachment header.
        attachment_filename: Name for the filename, if it differs
        add_etags: Set etags based on the filename, size and
            modification time.
        last_modified: Used to override the last modified value.
        cache_timeout: Time in seconds for the response to be cached.

    """
    file_path = file_path_to_path(filename)
    if attachment_filename is None:
        attachment_filename = file_path.name
    if mimetype is None:
        mimetype = mimetypes.guess_type(attachment_filename)[0] or DEFAULT_MIMETYPE
    file_body = current_app.response_class.file_body_class(file_path)
    response = current_app.response_class(file_body, mimetype=mimetype)

    if as_attachment:
        response.headers.add('Content-Disposition', 'attachment', filename=attachment_filename)

    if last_modified is not None:
        response.last_modified = last_modified
    else:
        response.last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)

    response.cache_control.public = True
    cache_timeout = cache_timeout or current_app.get_send_file_max_age(file_path)
    if cache_timeout is not None:
        response.cache_control.max_age = cache_timeout
        response.expires = datetime.utcnow() + timedelta(seconds=cache_timeout)

    if add_etags:
        response.set_etag(
            '{}-{}-{}'.format(
                file_path.stat().st_mtime, file_path.stat().st_size,
                adler32(bytes(file_path)),
            ),
        )

    if conditional:
        await response.make_conditional(request.range)
    return response
