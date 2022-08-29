from __future__ import annotations

from pathlib import Path

from quart.app import Quart


async def test_host_matching() -> None:
    app = Quart(__name__, static_folder="./assets", static_url_path="/static")

    test_client = app.test_client()

    response = await test_client.get("/static/config.cfg")
    assert response.status_code == 200
    data = await response.get_data(as_text=False)
    expected_data = (Path(__file__).parent / "assets/config.cfg").read_bytes()
    assert data == expected_data

    response = await test_client.get("/static/foo")
    assert response.status_code == 404

    # Should not be able to escape !
    response = await test_client.get("/static/../foo")
    assert response.status_code == 404

    response = await test_client.get("/static/../assets/config.cfg")
    assert response.status_code == 404

    # Non-escaping path with ..
    response = await test_client.get("/static/foo/../config.cfg")
    assert response.status_code == 200
    data = await response.get_data(as_text=False)
    assert data == expected_data
