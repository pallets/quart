from typing import Any, List, Union

from jinja2 import Template

from quart.flask_ext.globals import current_app
from quart.signals import before_render_template, template_rendered


def render_template(template_name_or_list: Union[str, List[str]], **context: Any) -> str:
    """Render the template with the context given.

    Arguments:
        template_name_or_list: Template name to render of a list of
            possible template names.
        context: The variables to pass to the template.
    """
    current_app.update_template_context(context)
    template = current_app.jinja_env.get_or_select_template(template_name_or_list)
    return _render(template, context)


def render_template_string(source: str, **context: Any) -> str:
    """Render the template source with the context given.

    Arguments:
        source: The template source code.
        context: The variables to pass to the template.
    """
    current_app.update_template_context(context)
    template = current_app.jinja_env.from_string(source)
    return _render(template, context)


def _render(template: Template, context: dict) -> str:
    app = current_app._get_current_object()
    before_render_template.send(app, template=template, context=context)
    rendered_template = template.render_async(context)  # type: ignore
    template_rendered.send(app, template=template, context=context)
    return rendered_template


__all__ = ('render_template', 'render_template_string')
