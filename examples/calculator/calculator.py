import ssl

from quart import abort, jsonify, Quart, render_template, request


app = Quart(__name__)


@app.route('/')
async def index():
    return await render_template('index.html')


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


if __name__ == '__main__':
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
    ssl_context.set_ciphers('ECDHE+AESGCM')
    ssl_context.load_cert_chain(certfile='examples/calculator/cert.pem', keyfile='examples/calculator/key.pem')
    ssl_context.set_alpn_protocols(['h2', 'http/1.1'])
    app.run(port=5000, ssl=ssl_context)
