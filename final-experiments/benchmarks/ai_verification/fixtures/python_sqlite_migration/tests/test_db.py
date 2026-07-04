import pytest
from src.db import init_db, create_user, get_user, list_users


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    import src.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    init_db()


def test_create_and_get_user():
    user = create_user("Alice", "alice@example.com")
    assert user["name"] == "Alice"
    fetched = get_user(user["id"])
    assert fetched is not None
    assert fetched["email"] == "alice@example.com"


def test_list_users_empty_initially():
    assert list_users() == []


def test_list_users_after_create():
    create_user("Bob", "bob@example.com")
    create_user("Carol", "carol@example.com")
    users = list_users()
    assert len(users) == 2
    names = {u["name"] for u in users}
    assert names == {"Bob", "Carol"}


def test_duplicate_email_raises():
    create_user("Alice", "alice@example.com")
    with pytest.raises(Exception):
        create_user("Alice2", "alice@example.com")
