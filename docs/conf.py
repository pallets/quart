import importlib.metadata
import os

from sphinx.ext import apidoc

# Project --------------------------------------------------------------

project = "Quart"
copyright = "2017 Pallets"
version = release = importlib.metadata.version("quart").partition(".dev")[0]

# General --------------------------------------------------------------

default_role = "code"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "myst_parser",
]
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = True
myst_enable_extensions = [
    "fieldlist",
]
myst_heading_anchors = 2

# HTML -----------------------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "external_links": [
        {"name": "Source code", "url": "https://github.com/pallets/quart"},
        {"name": "Issues", "url": "https://github.com/pallets/quart/issues"},
    ],
    "icon_links": [
        {
            "name": "Github",
            "url": "https://github.com/pallets/quart",
            "icon": "fab fa-github",
        },
    ],
}
html_static_path = ["_static"]
html_logo = "_static/logo_short.png"


def run_apidoc(_):
    # generate API documentation via sphinx-apidoc
    # https://www.sphinx-doc.org/en/master/man/sphinx-apidoc.html
    base_path = os.path.abspath(os.path.dirname(__file__))
    apidoc.main(
        [
            "-f",
            "-e",
            "-o",
            f"{base_path}/reference/source",
            f"{base_path}/../src/quart",
            f"{base_path}/../src/quart/datastructures.py",
        ]
    )


def setup(app):
    app.connect("builder-inited", run_apidoc)
