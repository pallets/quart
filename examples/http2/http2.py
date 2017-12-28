import ssl

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
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
    ssl_context.set_ciphers('ECDHE+AESGCM')
    ssl_context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    ssl_context.set_alpn_protocols(['h2', 'http/1.1'])
    app.run(port=5000, ssl=ssl_context)
