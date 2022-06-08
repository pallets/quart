from video import app


async def test_auto_video() -> None:
    test_client = app.test_client()
    response = await test_client.get("/video.mp4")
    data = await response.get_data()
    assert len(data) == 255_849

    response = await test_client.get("/video.mp4", headers={"Range": "bytes=200-1000"})
    data = await response.get_data()
    assert len(data) == 801


async def test_chunked_video() -> None:
    test_client = app.test_client()
    response = await test_client.get("/chunked_video.mp4")
    data = await response.get_data()
    assert len(data) == 255_849

    response = await test_client.get("/chunked_video.mp4", headers={"Range": "bytes=200-200000"})
    data = await response.get_data()
    assert len(data) == 100_000
