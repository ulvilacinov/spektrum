from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    (dist / "assets" / "index-abc.js").write_text("console.log(1)", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    return dist


@pytest.fixture
def frontend_client(settings: Settings, dist: Path) -> TestClient:
    return TestClient(create_app(settings.model_copy(update={"frontend_dist_dir": dist})))


def test_serves_index_for_client_side_routes(frontend_client: TestClient) -> None:
    for path in ("/", "/documents/2", "/sessions/14/quiz"):
        response = frontend_client.get(path)
        assert response.status_code == 200
        assert "id=root" in response.text
        assert response.headers["content-type"].startswith("text/html")


def test_serves_built_files(frontend_client: TestClient) -> None:
    assert frontend_client.get("/assets/index-abc.js").text == "console.log(1)"
    assert frontend_client.get("/favicon.svg").text == "<svg/>"


def test_does_not_leave_the_build_directory(frontend_client: TestClient) -> None:
    response = frontend_client.get("/..%2Fsecret.txt")
    assert "secret" not in response.text


def test_unknown_api_paths_stay_json_404(frontend_client: TestClient) -> None:
    response = frontend_client.get("/api/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_api_is_unaffected(frontend_client: TestClient) -> None:
    assert frontend_client.get("/openapi.json").status_code == 200


def test_without_setting_only_the_api_is_served(settings: Settings) -> None:
    client = TestClient(create_app(settings))
    assert client.get("/documents/2").status_code == 404


def test_missing_build_fails_fast(settings: Settings, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="npm run build"):
        create_app(settings.model_copy(update={"frontend_dist_dir": tmp_path / "missing"}))
