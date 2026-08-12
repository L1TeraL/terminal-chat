import pytest

from client import client
from shared import config, protocol


class FakeSocket:
    def __init__(self, responses=None):
        self.sent_data = None
        self.responses = responses or []
        self.closed = False

    def sendall(self, data):
        self.sent_data = data

    def recv(self, buffer_size):
        if not self.responses:
            return b""

        return self.responses.pop(0)

    def shutdown(self, how):
        pass

    def close(self):
        self.closed = True


# send_message

def test_send_message():
    client_socket = FakeSocket()

    result = client.send_message(
        client_socket,
        "Hello"
    )

    assert result is True
    assert client_socket.sent_data == b"Hello"


def test_send_message_failed():
    class BrokenSocket(FakeSocket):
        def sendall(self, data):
            raise BrokenPipeError

    client_socket = BrokenSocket()

    result = client.send_message(
        client_socket,
        "Hello"
    )

    assert result is False


# receive_messages

def test_receive_messages_chat(capsys):
    packet = protocol.encode_message(
        protocol.COMMAND_CHAT,
        "Alex: Hello"
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    stop_event = __import__("threading").Event()
    login_queue = __import__("queue").Queue()

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
    )

    captured = capsys.readouterr()

    assert "Alex: Hello" in captured.out
    assert stop_event.is_set()


def test_receive_messages_login_ok():
    packet = protocol.encode_message(
        protocol.COMMAND_LOGIN_OK,
        "Welcome, Alex!"
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    import threading
    from queue import Queue

    stop_event = threading.Event()
    login_queue = Queue()

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
    )

    success, message = login_queue.get()

    assert success is True
    assert message == ""
    assert stop_event.is_set()


def test_receive_messages_login_failed():
    packet = protocol.encode_message(
        protocol.COMMAND_LOGIN_FAILED,
        "Username already in taken."
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    import threading
    from queue import Queue

    stop_event = threading.Event()
    login_queue = Queue()

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
    )

    success, message = login_queue.get()

    assert success is False
    assert message == "Username already in taken."
    assert stop_event.is_set()


def test_receive_messages_info(capsys):
    packet = protocol.encode_message(
        protocol.COMMAND_INFO,
        "Bob joined the chat."
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    import threading
    from queue import Queue

    stop_event = threading.Event()
    login_queue = Queue()

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
    )

    captured = capsys.readouterr()

    assert "[SERVER] Bob joined the chat." in captured.out


def test_receive_messages_error(capsys):
    packet = protocol.encode_message(
        protocol.COMMAND_ERROR,
        "Something went wrong."
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    import threading
    from queue import Queue

    stop_event = threading.Event()
    login_queue = Queue()

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
    )

    captured = capsys.readouterr()

    assert "[ERROR] Something went wrong." in captured.out


def test_receive_messages_user_list(capsys):
    packet = protocol.encode_message(
        protocol.COMMAND_USER_LIST,
        ["Alex", "Bob", "Piter"]
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    import threading
    from queue import Queue

    stop_event = threading.Event()
    login_queue = Queue()

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
    )

    captured = capsys.readouterr()

    assert "[SERVER] Online 3" in captured.out
    assert "- Alex" in captured.out
    assert "- Bob" in captured.out
    assert "- Piter" in captured.out


def test_receive_messages_invalid_packet(capsys):
    client_socket = FakeSocket(
        responses=[
            b"INVALID_PACKET\n"
        ]
    )

    import threading
    from queue import Queue

    stop_event = threading.Event()
    login_queue = Queue()

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
    )

    captured = capsys.readouterr()

    assert "[ERROR] Invalid packet received." in captured.out


# request_username

def test_request_username(monkeypatch):
    import threading
    from queue import Queue

    client_socket = FakeSocket()
    login_queue = Queue()

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "Alex"
    )

    login_queue.put(
        (
            True,
            ""
        )
    )

    stop_event = threading.Event()

    result = client.request_username(
        client_socket,
        login_queue,
        stop_event,
    )

    assert result is True

    command, payload = protocol.decode_message(
        client_socket.sent_data.decode(
            config.ENCODING
        ).strip()
    )

    assert command == protocol.COMMAND_SET_NAME
    assert payload == "Alex"


def test_request_username_empty_then_valid(monkeypatch, capsys):
    import threading
    from queue import Queue

    client_socket = FakeSocket()
    login_queue = Queue()

    usernames = iter([
        "",
        "Alex",
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(usernames)
    )

    login_queue.put(
        (
            True,
            ""
        )
    )

    stop_event = threading.Event()

    result = client.request_username(
        client_socket,
        login_queue,
        stop_event,
    )

    captured = capsys.readouterr()

    assert result is True
    assert "[SERVER] Username cannot be empty." in captured.out


def test_request_username_login_failed_then_success(
    monkeypatch,
    capsys,
):
    import threading
    from queue import Queue

    client_socket = FakeSocket()
    login_queue = Queue()

    usernames = iter([
        "Alex",
        "Bob",
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(usernames)
    )

    login_queue.put(
        (
            False,
            "Username already in taken."
        )
    )

    login_queue.put(
        (
            True,
            ""
        )
    )

    stop_event = threading.Event()

    result = client.request_username(
        client_socket,
        login_queue,
        stop_event,
    )

    captured = capsys.readouterr()

    assert result is True
    assert "Username already in taken." in captured.out


def test_request_username_stop_event(monkeypatch):
    import threading
    from queue import Queue

    client_socket = FakeSocket()
    login_queue = Queue()

    stop_event = threading.Event()
    stop_event.set()

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "Alex"
    )

    result = client.request_username(
        client_socket,
        login_queue,
        stop_event,
    )

    assert result is False
    assert client_socket.sent_data is None


# chat_loop

def test_chat_loop_send_message(monkeypatch):
    client_socket = FakeSocket()

    messages = iter([
        "Hello",
        "/quit",
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda: next(messages)
    )

    import threading

    stop_event = threading.Event()

    result = client.chat_loop(
        client_socket,
        stop_event,
    )

    assert result is None

    command, payload = protocol.decode_message(
        client_socket.sent_data.decode(
            config.ENCODING
        ).strip()
    )

    assert command == protocol.COMMAND_QUIT
    assert payload == ""


def test_chat_loop_online(monkeypatch):
    client_socket = FakeSocket()

    messages = iter([
        "/online",
        "/quit",
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda: next(messages)
    )

    import threading

    stop_event = threading.Event()

    client.chat_loop(
        client_socket,
        stop_event,
    )

    command, payload = protocol.decode_message(
        client_socket.sent_data.decode(
            config.ENCODING
        ).strip()
    )

    assert command == protocol.COMMAND_QUIT
    assert payload == ""


def test_chat_loop_empty_message(monkeypatch):
    client_socket = FakeSocket()

    messages = iter([
        "",
        "   ",
        "/quit",
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda: next(messages)
    )

    import threading

    stop_event = threading.Event()

    client.chat_loop(
        client_socket,
        stop_event,
    )

    command, payload = protocol.decode_message(
        client_socket.sent_data.decode(
            config.ENCODING
        ).strip()
    )

    assert command == protocol.COMMAND_QUIT


def test_chat_loop_send_failed():
    class BrokenSocket(FakeSocket):
        def sendall(self, data):
            raise BrokenPipeError

    client_socket = BrokenSocket()

    import threading

    stop_event = threading.Event()

    inputs = iter([
        "Hello"
    ])

    import builtins

    original_input = builtins.input

    try:
        builtins.input = lambda: next(inputs)

        result = client.chat_loop(
            client_socket,
            stop_event,
        )
    finally:
        builtins.input = original_input

    assert result is None
    assert stop_event.is_set()