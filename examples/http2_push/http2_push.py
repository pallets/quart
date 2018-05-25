from collections import namedtuple
from io import BytesIO
import os
import ssl

import click
from PIL import Image
from quart import (
    make_response, Quart, render_template, url_for
)


app = Quart(__name__)

Point = namedtuple('Point', ('x', 'y'))


class TileOutOfBoundsError(Exception):
    pass


def get_tile(tile_number):
    """
    Returns a crop of `img` based on a sequence number `tile_number`.

    :param int tile_number: Number of the tile between 0 and `max_tiles`^2.
    :raises TileOutOfBoundsError: When `tile_number` exceeds `max_tiles`^2
    :rtype PIL.Image:
    """
    tile_number = int(tile_number)
    max_tiles = app.max_tiles
    if tile_number > max_tiles * max_tiles:
        raise TileOutOfBoundsError('Requested an out of bounds tile')

    tile_size = Point(
        app.img.size[0] // max_tiles, app.img.size[1] // max_tiles)
    tile_coords = Point(
        tile_number % max_tiles, tile_number // max_tiles)
    crop_box = (
        tile_coords.x * tile_size.x,
        tile_coords.y * tile_size.y,
        tile_coords.x * tile_size.x + tile_size.x,
        tile_coords.y * tile_size.y + tile_size.y,
    )
    return app.img.crop(crop_box)


@app.route('/')
async def index():
    response = await make_response(
        await render_template(
            'index.html',
            max_tiles=app.max_tiles, title='Using standard HTTP/2'))
    response.push_promises.add(url_for('static', filename='style.css'))
    return response


@app.route('/push')
async def push():
    response = await make_response(
        await render_template(
            'index.html',
            max_tiles=app.max_tiles, title='Using push promises'))
    response.push_promises.add(url_for('static', filename='style.css'))
    for i in range(app.max_tiles * app.max_tiles):
        response.push_promises.add(url_for('tile', tile_number=i))
    return response


@app.route('/tile/<int:tile_number>')
async def tile(tile_number):
    """
    Handles GET requests for a tile number.

    :param int tile_number: Number of the tile between 0 and `max_tiles`^2.
    :raises HTTPError: 404 if tile exceeds `max_tiles`^2.
    """
    try:
        tile = get_tile(tile_number)
    except TileOutOfBoundsError:
        return 'Not found', 404

    buf = BytesIO(tile.tobytes())
    tile.save(buf, 'JPEG')

    content = buf.getvalue()
    response = await make_response(content)
    response.headers['Content-Type'] = 'image/jpg'
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Content-Length'] = str(len(content))
    return response


@app.cli.command('run')
@click.option('--image_name', default='burmese_python.jpg')
@click.option('--max_tiles', default=8)
def run(image_name, max_tiles):
    base_path = os.path.dirname(__file__)
    path_to_image = os.path.join(base_path, 'static', image_name)
    app.img = Image.open(path_to_image)
    app.max_tiles = max_tiles

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.options |= (
        ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION)
    ssl_context.set_ciphers('ECDHE+AESGCM')
    ssl_context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    ssl_context.set_alpn_protocols(['h2', 'http/1.1'])
    app.run(port=5000, ssl=ssl_context)
