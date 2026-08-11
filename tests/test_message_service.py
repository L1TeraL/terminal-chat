import pytest

from server import message_service, client_registry
from shared import protocol, config


class FakeSocket:
    def __init__(self):
        self.sent_data = None

    def sendall(self, data):
        self.sent_data = data

class BrokenSocket:
    def sendall(self, data):
        raise BrokenPipeError

@pytest.fixture(autouse=True)
def clear_clients():
    client_registry.clean_clients()
    yield
    client_registry.clean_clients()

def test_send_to_client():
    client_socket = FakeSocket()

    result = message_service.send_to_client(
        client_socket,
        "Hello"
    )

    assert result is True
    assert client_socket.sent_data == b"Hello"

def test_send_to_client_failed():
    client_socket = BrokenSocket()

    result = message_service.send_to_client(
        client_socket,
        "Hello"
    )

    assert result is False

def test_broadcast_chat():
    sender = FakeSocket()
    client_2 = FakeSocket()
    client_3 = FakeSocket()

    client_registry.add_client(sender, '0.0.0.0')
    client_registry.add_client(client_2, '0.0.0.0')
    client_registry.add_client(client_3, '0.0.0.0')

    client_registry.set_client_name(sender, 'Alex')

    message_service.broadcast_chat(sender, 'Hello')

    assert sender.sent_data is None
    assert client_2.sent_data is not None
    assert client_3.sent_data is not None

    command, payload = protocol.decode_message(
        client_2.sent_data.decode(config.ENCODING).strip()
    )

    assert command == protocol.COMMAND_CHAT
    assert payload == 'Alex: Hello'

def test_handle_chat_not_in_chat():
    client = FakeSocket()

    client_registry.add_client(client, '0.0.0.0')

    result = message_service._handle_chat(
        client,
        'Hello'
    )

    assert result is False
    assert client.sent_data is None

def test_handle_chat():
    client_1 = FakeSocket()
    client_2 = FakeSocket()

    client_registry.add_client(client_1, '0.0.0.0')
    client_registry.add_client(client_2, '0.0.0.0')

    client_registry.set_client_name(client_1, 'Alex')
    client_registry.set_client_name(client_2, 'Bob')

    client_registry.set_client_state(client_1, protocol.STATE_CHAT)

    result = message_service._handle_chat(
        client_1,
        'Hello'
    )

    assert result is True

    command, payload = protocol.decode_message(
        client_2.sent_data.decode(config.ENCODING).strip()
    )

    assert command == protocol.COMMAND_CHAT
    assert payload == 'Alex: Hello'
    assert client_1.sent_data is None

def test_hande_chat_empty_message():
    client_1 = FakeSocket()

    client_registry.add_client(client_1, '0.0.0.0')

    client_registry.set_client_state(client_1, protocol.STATE_CHAT)

    result = message_service._handle_chat(
        client_1,
        ' '
    )

    assert result is False
    assert client_1.sent_data is None

def test_handle_set_name():
    client_1 = FakeSocket()

    client_registry.add_client(client_1, '0.0.0.0')

    result = message_service._handle_set_name(
        client_1,
        'Alex'
    )

    assert result is True

    assert client_registry.get_client_name(client_1) == 'Alex'
    assert client_registry.get_client_state(client_1) == protocol.STATE_CHAT

def test_handle_set_name_invalid():
    client_1 = FakeSocket()

    client_registry.add_client(client_1, '0.0.0.0')

    result = message_service._handle_set_name(
        client_1,
        'Al'
    )

    assert result is False

    assert client_registry.get_client_name(client_1) is None
    assert client_registry.get_client_state(client_1) == protocol.STATE_WAIT_USERNAME

def test_handle_set_name_username_unavailable():
    client_1 = FakeSocket()
    client_2 = FakeSocket()

    client_registry.add_client(client_1, '0.0.0.0')
    client_registry.add_client(client_2, '0.0.0.0')

    client_registry.set_client_name(client_1, 'Alex')

    result = message_service._handle_set_name(client_2, 'Alex')

    assert result is False
    assert client_registry.get_client_name(client_1) == 'Alex'
    assert client_registry.get_client_name(client_2) is None
    assert client_registry.get_client_state(client_2) == protocol.STATE_WAIT_USERNAME

def test_handle_online():
    client_1 = FakeSocket()
    client_2 = FakeSocket()
    client_3 = FakeSocket()

    client_registry.add_client(client_1, '0.0.0.0')
    client_registry.add_client(client_2, '0.0.0.0')
    client_registry.add_client(client_3, '0.0.0.0')

    client_registry.set_client_name(client_1, 'Alex')
    client_registry.set_client_name(client_2, 'Bob')
    client_registry.set_client_name(client_3, 'Piter')

    client_registry.set_client_state(client_1, protocol.STATE_CHAT)
    client_registry.set_client_state(client_2, protocol.STATE_CHAT)
    client_registry.set_client_state(client_3, protocol.STATE_CHAT)

    result = message_service._handle_online(client_1)

    assert result is True
    assert client_1.sent_data is not None
    assert client_2.sent_data is None
    assert client_3.sent_data is None

    command, payload = protocol.decode_message(
        client_1.sent_data.decode(config.ENCODING).strip()
    )

    assert command == protocol.COMMAND_USER_LIST
    assert payload == ["Alex", "Bob", "Piter"]

def test_process_message_chat(monkeypatch):
    client = FakeSocket()

    def fake_handle_chat(client_socket, payload):
        return 'CHAT_CALLED'

    monkeypatch.setattr(
        message_service,
        '_handle_chat',
        fake_handle_chat)

    result = message_service.process_message(
        client,
        protocol.COMMAND_CHAT,
        'Hello'
    )

    assert result == 'CHAT_CALLED'

def test_process_message_set_name(monkeypatch):
    client = FakeSocket()

    def fake_handle_set_name(client_socket, payload):
        return 'CHAT_SET_NAME'

    monkeypatch.setattr(
        message_service,
        '_handle_set_name',
        fake_handle_set_name
    )

    result = message_service.process_message(
        client,
        protocol.COMMAND_SET_NAME,
        'Alex'
    )

    assert result == 'CHAT_SET_NAME'

def test_process_message_quit(monkeypatch):
    client = FakeSocket()

    def fake_handle_quit(client_socket):
        return 'QUIT_CALLED'

    monkeypatch.setattr(
        message_service,
        '_handle_quit',
        fake_handle_quit
    )

    result = message_service.process_message(
        client,
        protocol.COMMAND_QUIT,
        None
    )

    assert result == 'QUIT_CALLED'

def test_process_message_online(monkeypatch):
    client = FakeSocket()

    def fake_handle_online(client_socket):
        return 'CHAT_ONLINE'

    monkeypatch.setattr(
        message_service,
        '_handle_online',
        fake_handle_online
    )

    result = message_service.process_message(
        client,
        protocol.COMMAND_ONLINE,
        None
    )

    assert result == 'CHAT_ONLINE'

def test_process_message_unknown_command():
    client = FakeSocket()

    result = message_service.process_message(
        client,
        'UNKNOWN_COMMAND',
        None
    )

    assert result is False

def test_handle_quit():
    client_1 = FakeSocket()
    client_2 = FakeSocket()

    client_registry.add_client(client_1, '0.0.0.0')
    client_registry.add_client(client_2, '0.0.0.0')

    client_registry.set_client_name(client_1, 'Alex')
    client_registry.set_client_name(client_2, 'Bob')

    result = message_service._handle_quit(client_1)

    assert result == protocol.HANDLER_CLOSE
    assert client_1.sent_data is None
    assert client_2.sent_data is not None

    command, payload = protocol.decode_message(
        client_2.sent_data.decode(config.ENCODING).strip()
    )

    assert command == protocol.COMMAND_INFO
    assert payload == 'Alex left the chat.'






