import os
import shutil
import tempfile

import pytest


@pytest.fixture
def temp_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def config_path_override(temp_dir, monkeypatch):
    monkeypatch.setattr("src.config.get_config_dir", lambda: temp_dir)
    monkeypatch.setattr("src.config.get_config_path", lambda: os.path.join(temp_dir, "config.json"))
    monkeypatch.setattr("src.db.get_config_dir", lambda: temp_dir)
    return temp_dir


@pytest.fixture
def db_path_override(temp_dir, monkeypatch):
    monkeypatch.setattr("src.db.get_db_path", lambda: os.path.join(temp_dir, "test.db"))
    return os.path.join(temp_dir, "test.db")


@pytest.fixture
def clean_db(db_path_override):
    import src.db
    src.db.init_db()
    yield
    for path in (db_path_override, db_path_override + "-wal", db_path_override + "-shm"):
        try:
            os.remove(path)
        except (FileNotFoundError, PermissionError):
            pass
    src.db._db_write_lock = __import__("threading").Lock()
