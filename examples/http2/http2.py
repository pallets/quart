from quart import (
    abort, jsonify, make_response, Quart, render_template, request, url_for,
)


app = Quart(__name__)


@app.route('/')
async def index():
    response = await make_response(await render_template('index.html'))
    response.push_promises.add(url_for('static', filename='http2.css'))
    response.push_promises.add(url_for('static', filename='http2.js'))
    return response


@app.route('/', methods=['POST'])
async def calculate():
    data = await request.get_json()
    operator = data['operator']
    try:
        a = int(data['a'])
        b = int(data['b'])
    except ValueError:
        abort(400)
    if operator == '+':
        return jsonify(a + b)
    elif operator == '-':
        return jsonify(a - b)
    elif operator == '*':
        return jsonify(a * b)
    elif operator == '/':
        return jsonify(a / b)
    else:
        abort(400)


@app.cli.command('run')
def run():
    app.run(port=5000, certfile='cert.pem', keyfile='key.pem')
