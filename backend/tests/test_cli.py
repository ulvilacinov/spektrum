from pathlib import Path

from app.cli import ensure_secret_key


def test_adds_a_secret_key_once(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("DATABASE_URL=x\n", encoding="utf-8")

    assert ensure_secret_key(env) is True
    first = env.read_text(encoding="utf-8")
    assert first.startswith("DATABASE_URL=x\n")
    assert len(first.split("SECRET_KEY=")[1].strip()) >= 32

    assert ensure_secret_key(env) is False  # kept: changing it would lose the saved keys
    assert env.read_text(encoding="utf-8") == first


def test_fills_an_empty_secret_key_line(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("SECRET_KEY=\nOTHER=1\n", encoding="utf-8")

    assert ensure_secret_key(env) is True
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("SECRET_KEY=") and len(lines[0]) > len("SECRET_KEY=") + 30
    assert lines[1] == "OTHER=1"


def test_creates_the_file_if_missing(tmp_path: Path) -> None:
    env = tmp_path / ".env"

    assert ensure_secret_key(env) is True
    assert env.read_text(encoding="utf-8").startswith("# Encrypts")
