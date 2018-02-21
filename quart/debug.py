import inspect
import sys

from .templating import render_template_string
from .wrappers import Response


TEMPLATE = """
<style>
pre {
  margin: 0;
}

.traceback, .locals {
  display: table;
  width: 100%;
  margin: 5px;
}

.traceback>div, .locals>div {
  display: table-row;
}

.traceback>div>div, .locals>div>div {
  display: table-cell;
}

.locals>div>div {
  border-top: 1px solid lightgrey;
}

.header {
  background-color: #fbf9f9;
  margin-bottom: 5px;
}

.info {
  font-weight: bold;
}

li {
  border: 1px solid lightgrey;
  border-radius: 5px;
  padding: 5px;
  list-style-type: none;
  margin-bottom: 5px;
}

h1>span {
  font-weight: lighter;
}
</style>

<h1>{{ name }} <span>{{ value }}</span></h1>
<ul>
  {% for frame in frames %}
    <li>
      <div class="header">
        File <span class="info">{{ frame.file }}</span>,
        line <span class="info">{{ frame.line }}</span>, in
      </div>
      <div class="traceback">
        {% for line in frame.code[0] %}
          <div>
            <div>{{ loop.index + frame.code[1] }}</div>
            <div><pre>{{ line }}</pre></div>
          </div>
        {% endfor %}
      </div>
      <div class="locals">
        {% for name, repr in frame.locals.items() %}
          <div>
            <div>{{ name }}</div>
            <div>{{ repr }}</div>
          </div>
        {% endfor %}
      </div>
    </li>
  {% endfor %}
</ul>
"""


async def traceback_response() -> Response:
    type_, value, tb = sys.exc_info()
    frames = []
    while tb:
        frame = tb.tb_frame
        frames.append({
            'file': inspect.getfile(frame),
            'line': frame.f_lineno,
            'locals': frame.f_locals,
            'code': inspect.getsourcelines(frame),
        })
        tb = tb.tb_next

    name = type_.__name__
    html = await render_template_string(TEMPLATE, frames=reversed(frames), name=name, value=value)
    return Response(html, 500)
