import pytest

from server import client_registry
from shared import protocol


@pytest.fixture(autouse=True)
def clear_clients():
    client_registry.clean_clients()
    yield
    client_registry.clean_clients()

def test_add_client():
    client_registry.add_client(
        1,
        '0.0.0.0'
    )

    assert client_registry.get_client_state(1) == protocol.STATE_WAIT_USERNAME

def test_set_client_name():
    client_registry.add_client(
        1,
        '0.0.0.0'
    )

    client_registry.set_client_name(
        1,
        'Alex'
    )

    assert client_registry.get_client_name(1) == 'Alex'

def test_username_unavailable():
    client_registry.add_client(
        1,
        '0.0.0.0'
    )

    client_registry.set_client_name(
        1,
        'Alex'
    )

    assert client_registry.username_available('Alex') is False

def test_username_available():
    assert client_registry.username_available('Bob') is True

@pytest.mark.parametrize(
    "username, expected",
    [
        ("Alex", True),
        (" Alex ", True),
        ("Al", False),
        ("SERVER", False),
        ("[Alex]", False),
        ("INFO", False),
        ("None", False),
    ]
)
def test_validate_username(username, expected):
    assert client_registry.validate_username(username) == expected

def test_get_online_users():
    client_registry.add_client(
        1,
        '0.0.0.0'
    )
    client_registry.add_client(
        2,
        '0.0.0.0'
    )

    client_registry.set_client_name(
        1,
        'Alex'
    )

    assert client_registry.get_online_users() == ['Alex']

def test_set_client_state():
    client_registry.add_client(
        1,
        '0.0.0.0'
    )
    client_registry.set_client_state(
        1,
        protocol.STATE_CHAT
    )

    assert client_registry.get_client_state(1) == protocol.STATE_CHAT

def test_get_client_state_unknown_client():
    assert client_registry.get_client_state(777) is None

def test_set_client_state_unknown_client():
    assert client_registry.set_client_state(777, protocol.STATE_CHAT) is False

def test_set_client_name_unknown_client():
    assert client_registry.set_client_name(777, "Alex") is False

def test_get_client_name():
    client_registry.add_client(
        1,
        '0.0.0.0'
    )
    client_registry.set_client_name(
        1,
        'Alex'
    )
    assert client_registry.get_client_name(1) == 'Alex'

def test_get_client_name_unknown_client():
    assert client_registry.get_client_name(777) is None

def test_get_client_address():
    client_registry.add_client(
        1,
        '0.0.0.0'
    )

    assert client_registry.get_client_address(1) == '0.0.0.0'

def test_get_client_address_unknown_client():
    assert client_registry.get_client_address(777) is None

def test_remove_client():
    client_registry.add_client(
        1,
        '0.0.0.0'
    )
    client_registry.set_client_name(
        1,
        'Alex'
    )

    assert client_registry.remove_client(1) == 'Alex'
    assert client_registry.get_client_name(1) is None


