import pytest

from blog import app, _init_db


@pytest.fixture(name='test_app')
def _test_app(tmpdir):
    app.config['DATABASE'] = str(tmpdir.join('blog.db'))
    _init_db()
    return app


@pytest.mark.asyncio
async def test_create(test_app):
    test_client = test_app.test_client()
    await test_client.post(
        '/login/',
        form={
            'username': test_app.config['USERNAME'],
            'password': test_app.config['PASSWORD']
        },
    )
    response = await test_client.post(
        '/', form={'title': 'test_title', 'text': 'test_text'},
    )
    assert response.status_code == 301
    response = await test_client.get('/')
    body = await response.get_data(raw=False)
    assert 'test_title' in body
    assert 'test_text' in body
