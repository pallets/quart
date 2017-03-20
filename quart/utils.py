from .globals import current_app
from .wrappers import Response


def redirect(location: str, status_code: int=301) -> Response:
    body = """
<!doctype html>
<title>Redirect</title>
<h1>Redirect</h1>
You should be redirected to <a href="{0}">{0}</a>, it not please click the link
    """.format(location)

    return current_app.response_class(
           body, status_code=status_code, headers={'Location': location},
    )
