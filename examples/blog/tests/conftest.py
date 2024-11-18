import pytest
from blog import app
from blog import init_db


@pytest.fixture(autouse=True)
def configure_db(tmpdir):
    app.config["DATABASE"] = str(tmpdir.join("blog.db"))
    init_db()
