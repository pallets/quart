from __future__ import annotations

from typing import Any, AsyncIterator, TYPE_CHECKING

from flask.templating import DispatchingJinjaLoader as DispatchingJinjaLoader  # noqa: F401
from jinja2 import Environment as BaseEnvironment, Template

from .ctx import has_app_context, has_request_context
from .globals import app_ctx, current_app, request_ctx
from .helpers import stream_with_context
from .signals import before_render_template, template_rendered

if TYPE_CHECKING:
    from .app import Quart  # noqa


class Environment(BaseEnvironment):
    """Quart specific Jinja Environment.

    This changes the default Jinja loader to use the
    DispatchingJinjaLoader, and enables async Jinja by default.
    """

    def __init__(self, app: Quart, **options: Any) -> None:
        """Create a Quart specific Jinja Environment.

        Arguments:
            app: The Quart app to bind to.
            options: The standard Jinja Environment options.
        """
        if "loader" not in options:
            options["loader"] = app.create_global_jinja_loader()
        options["enable_async"] = True
        super().__init__(**options)


async def render_template(template_name_or_list: str | list[str], **context: Any) -> str:
    """Render the template with the context given.

    Arguments:
        template_name_or_list: Template name to render of a list of
            possible template names.
        context: The variables to pass to the template.
    """
    await current_app.update_template_context(context)
    template = current_app.jinja_env.get_or_select_template(template_name_or_list)  # type: ignore
    return await _render(template, context, current_app._get_current_object())  # type: ignore


async def render_template_string(source: str, **context: Any) -> str:
    """Render the template source with the context given.

    Arguments:
        source: The template source code.
        context: The variables to pass to the template.
    """
    await current_app.update_template_context(context)
    template = current_app.jinja_env.from_string(source)
    return await _render(template, context, current_app._get_current_object())  # type: ignore


async def _render(template: Template, context: dict, app: Quart) -> str:
    await before_render_template.send_async(
        app, _sync_wrapper=app.ensure_async, template=template, context=context  # type: ignore
    )
    rendered_template = await template.render_async(context)
    await template_rendered.send_async(
        app, _sync_wrapper=app.ensure_async, template=template, context=context  # type: ignore
    )
    return rendered_template


async def _default_template_ctx_processor() -> dict[str, Any]:
    context = {}
    if has_app_context():
        context["g"] = app_ctx.g
    if has_request_context():
        context["request"] = request_ctx.request
        context["session"] = request_ctx.session
    return context


async def stream_template(
    template_name_or_list: str | Template | list[str | Template], **context: Any
) -> AsyncIterator[str]:
    """Render a template by name with the given context as a stream.

    This returns an iterator of strings, which can be used as a
    streaming response from a view.

    Arguments:
        template_name_or_list: The name of the template to render. If a
            list is given, the first name to exist will be rendered.
        context: The variables to make available in the template.
    """
    await current_app.update_template_context(context)
    template = current_app.jinja_env.get_or_select_template(template_name_or_list)
    return await _stream(current_app._get_current_object(), template, context)  # type: ignore


async def stream_template_string(source: str, **context: Any) -> AsyncIterator[str]:
    """Render a template from the given source with the *context* as a stream.

    This returns an iterator of strings, which can
    be used as a streaming response from a view.

    Arguments:
        source: The source code of the template to render.
        context: The variables to make available in the template.
    """
    await current_app.update_template_context(context)
    template = current_app.jinja_env.from_string(source)
    return await _stream(current_app._get_current_object(), template, context)  # type: ignore


async def _stream(app: Quart, template: Template, context: dict[str, Any]) -> AsyncIterator[str]:
    await before_render_template.send_async(
        app, _sync_wrapper=app.ensure_async, template=template, context=context  # type: ignore
    )

    async def generate() -> AsyncIterator[str]:
        async for chunk in template.generate_async(context):
            yield chunk
        await template_rendered.send_async(
            app, _sync_wrapper=app.ensure_async, template=template, context=context  # type: ignore
        )

    # If a request context is active, keep it while generating.
    if has_request_context():
        return stream_with_context(generate)()
    else:
        return generate()
