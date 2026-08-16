import pytest

from server.message_history import MessageHistory


@pytest.fixture
def db(tmp_path):
    return MessageHistory(db_name=tmp_path / "test.db")


def test_create_table(db):
    with db._get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='chat_messages';
        """)

        table_exists = cursor.fetchone()

        assert table_exists is not None
        assert table_exists[0] == "chat_messages"


def test_add_message(db):
    db.add_message("User1", "Hello")

    history = db.get_chat_history()

    assert len(history) == 1
    assert history[0][1] == "User1"
    assert history[0][2] == "Hello"


def test_get_chat_history(db):
    db.add_message("User1", "Message1")
    db.add_message("User2", "Message2")
    db.add_message("User3", "Message3")
    db.add_message("User4", "Message4")

    history = db.get_chat_history(limit=3)

    assert len(history) == 3
    assert history[0][2] == "Message2"
    assert history[1][2] == "Message3"
    assert history[2][2] == "Message4"


def test_get_history_empty_db(db):
    history = db.get_chat_history()

    assert history == []


def test_get_chat_history_limit(db):
    for i in range(25):
        db.add_message(
            f"User{i}",
            f"Message{i}",
        )

    history = db.get_chat_history(limit=20)

    assert len(history) == 20
    assert history[0][2] == "Message5"
    assert history[-1][2] == "Message24"