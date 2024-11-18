from blog import app


async def test_create_post():
    test_client = app.test_client()
    response = await test_client.post(
        "/create/", form={"title": "Post", "text": "Text"}
    )
    assert response.status_code == 302
    response = await test_client.get("/")
    text = await response.get_data()
    assert b"<h2>Post</h2>" in text
    assert b"<p>Text</p>" in text
