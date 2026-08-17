import threading
from queue import Queue

from client import client
from shared import config, protocol


class FakeSocket:
    def __init__(self, responses=None):
        self.sent_data = []
        self.responses = responses or []
        self.closed = False

    def sendall(self, data):
        self.sent_data.append(data)

    def recv(self, buffer_size):
        if not self.responses:
            return b""

        return self.responses.pop(0)

    def shutdown(self, how):
        pass

    def close(self):
        self.closed = True


# ============================================================
# send_message
# ============================================================

def test_send_message():
    client_socket = FakeSocket()

    result = client.send_message(
        client_socket,
        "Hello",
    )

    assert result is True
    assert client_socket.sent_data == [b"Hello"]


def test_send_message_failed():
    class BrokenSocket(FakeSocket):
        def sendall(self, data):
            raise BrokenPipeError

    client_socket = BrokenSocket()

    result = client.send_message(
        client_socket,
        "Hello",
    )

    assert result is False


# ============================================================
# receive_messages
# ============================================================

def test_receive_messages_chat(monkeypatch):
    packet = protocol.encode_message(
        protocol.COMMAND_CHAT,
        "Alex: Hello",
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    stop_event = threading.Event()
    login_queue = Queue()
    history_queue = Queue()

    received = []

    monkeypatch.setattr(
        client.ui,
        "show_chat_message",
        lambda message: received.append(message),
    )

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
        history_queue,
    )

    assert received == ["Alex: Hello"]
    assert stop_event.is_set()


def test_receive_messages_login_ok():
    packet = protocol.encode_message(
        protocol.COMMAND_LOGIN_OK,
        "Welcome, Alex!",
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    stop_event = threading.Event()
    login_queue = Queue()
    history_queue = Queue()

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
        history_queue,
    )

    success, message = login_queue.get()

    assert success is True
    assert message == "Welcome, Alex!"
    assert stop_event.is_set()


def test_receive_messages_login_failed():
    packet = protocol.encode_message(
        protocol.COMMAND_LOGIN_FAILED,
        "Username already in taken.",
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    stop_event = threading.Event()
    login_queue = Queue()
    history_queue = Queue()

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
        history_queue,
    )

    success, message = login_queue.get()

    assert success is False
    assert message == "Username already in taken."
    assert stop_event.is_set()


def test_receive_messages_info(monkeypatch):
    packet = protocol.encode_message(
        protocol.COMMAND_INFO,
        "Bob joined the chat.",
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    stop_event = threading.Event()
    login_queue = Queue()
    history_queue = Queue()

    received = []

    monkeypatch.setattr(
        client.ui,
        "show_info",
        lambda message: received.append(message),
    )

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
        history_queue,
    )

    assert "Bob joined the chat." in received


def test_receive_messages_error(monkeypatch):
    packet = protocol.encode_message(
        protocol.COMMAND_ERROR,
        "Something went wrong.",
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    stop_event = threading.Event()
    login_queue = Queue()
    history_queue = Queue()

    received = []

    monkeypatch.setattr(
        client.ui,
        "show_error",
        lambda message: received.append(message),
    )

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
        history_queue,
    )

    assert received == ["Something went wrong."]


def test_receive_messages_user_list(monkeypatch):
    users = ["Alex", "Bob", "Piter"]

    packet = protocol.encode_message(
        protocol.COMMAND_USER_LIST,
        users,
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    stop_event = threading.Event()
    login_queue = Queue()
    history_queue = Queue()

    received = []

    monkeypatch.setattr(
        client.ui,
        "show_users",
        lambda users: received.append(users),
    )

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
        history_queue,
    )

    assert received == [users]


def test_receive_messages_chat_history():
    history = [
        [1, "Alex", "Hello", "2026-08-17 17:00:00"],
        [2, "Bob", "Hi", "2026-08-17 17:01:00"],
    ]

    packet = protocol.encode_message(
        protocol.COMMAND_CHAT_HISTORY,
        history,
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    stop_event = threading.Event()
    login_queue = Queue()
    history_queue = Queue()

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
        history_queue,
    )

    received_history = history_queue.get()

    assert received_history == history


def test_receive_messages_invalid_packet(monkeypatch):
    client_socket = FakeSocket(
        responses=[
            b"INVALID_PACKET\n",
        ]
    )

    stop_event = threading.Event()
    login_queue = Queue()
    history_queue = Queue()

    errors = []

    monkeypatch.setattr(
        client.ui,
        "show_error",
        lambda message: errors.append(message),
    )

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
        history_queue,
    )

    assert errors == [
        "Invalid packet received."
    ]


def test_receive_messages_unknown_command(monkeypatch):
    packet = protocol.encode_message(
        "UNKNOWN_COMMAND",
        "test",
    )

    client_socket = FakeSocket(
        responses=[
            packet.encode(config.ENCODING),
        ]
    )

    stop_event = threading.Event()
    login_queue = Queue()
    history_queue = Queue()

    errors = []

    monkeypatch.setattr(
        client.ui,
        "show_error",
        lambda message: errors.append(message),
    )

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
        history_queue,
    )

    assert errors == [
        "Unknown command: UNKNOWN_COMMAND"
    ]


def test_receive_messages_server_disconnected(monkeypatch):
    client_socket = FakeSocket(
        responses=[
            b"",
        ]
    )

    stop_event = threading.Event()
    login_queue = Queue()
    history_queue = Queue()

    messages = []

    monkeypatch.setattr(
        client.ui,
        "show_info",
        lambda message: messages.append(message),
    )

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
        history_queue,
    )

    assert messages == ["Server disconnected."]
    assert stop_event.is_set()


def test_receive_messages_connection_lost(monkeypatch):
    class BrokenSocket(FakeSocket):
        def recv(self, buffer_size):
            raise ConnectionResetError

    client_socket = BrokenSocket()

    stop_event = threading.Event()
    login_queue = Queue()
    history_queue = Queue()

    errors = []

    monkeypatch.setattr(
        client.ui,
        "show_error",
        lambda message: errors.append(message),
    )

    client.receive_messages(
        client_socket,
        stop_event,
        login_queue,
        history_queue,
    )

    assert errors == ["Connection lost."]
    assert stop_event.is_set()


# ============================================================
# request_username
# ============================================================

def test_request_username(monkeypatch):
    client_socket = FakeSocket()
    login_queue = Queue()

    monkeypatch.setattr(
        client.ui,
        "ask_username",
        lambda: "Alex",
    )

    login_queue.put(
        (
            True,
            "Welcome, Alex!",
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
        client_socket.sent_data[0]
        .decode(config.ENCODING)
        .strip()
    )

    assert command == protocol.COMMAND_SET_NAME
    assert payload == "Alex"


def test_request_username_empty_then_valid(monkeypatch):
    client_socket = FakeSocket()
    login_queue = Queue()

    usernames = iter([
        "",
        "Alex",
    ])

    monkeypatch.setattr(
        client.ui,
        "ask_username",
        lambda: next(usernames),
    )

    login_queue.put(
        (
            True,
            "Welcome, Alex!",
        )
    )

    errors = []

    monkeypatch.setattr(
        client.ui,
        "show_error",
        lambda message: errors.append(message),
    )

    stop_event = threading.Event()

    result = client.request_username(
        client_socket,
        login_queue,
        stop_event,
    )

    assert result is True
    assert errors == [
        "Username cannot be empty."
    ]

    command, payload = protocol.decode_message(
        client_socket.sent_data[0]
        .decode(config.ENCODING)
        .strip()
    )

    assert command == protocol.COMMAND_SET_NAME
    assert payload == "Alex"


def test_request_username_login_failed_then_success(monkeypatch):
    client_socket = FakeSocket()
    login_queue = Queue()

    usernames = iter([
        "Alex",
        "Bob",
    ])

    monkeypatch.setattr(
        client.ui,
        "ask_username",
        lambda: next(usernames),
    )

    login_queue.put(
        (
            False,
            "Username already in taken.",
        )
    )

    login_queue.put(
        (
            True,
            "Welcome, Bob!",
        )
    )

    failed_messages = []

    monkeypatch.setattr(
        client.ui,
        "show_login_failed",
        lambda message: failed_messages.append(message),
    )

    monkeypatch.setattr(
        client.ui,
        "show_login_success",
        lambda username: None,
    )

    stop_event = threading.Event()

    result = client.request_username(
        client_socket,
        login_queue,
        stop_event,
    )

    assert result is True
    assert failed_messages == [
        "Username already in taken."
    ]

    assert len(client_socket.sent_data) == 2

    command, payload = protocol.decode_message(
        client_socket.sent_data[0]
        .decode(config.ENCODING)
        .strip()
    )

    assert command == protocol.COMMAND_SET_NAME
    assert payload == "Alex"

    command, payload = protocol.decode_message(
        client_socket.sent_data[1]
        .decode(config.ENCODING)
        .strip()
    )

    assert command == protocol.COMMAND_SET_NAME
    assert payload == "Bob"


def test_request_username_send_failed(monkeypatch):
    class BrokenSocket(FakeSocket):
        def sendall(self, data):
            raise BrokenPipeError

    client_socket = BrokenSocket()
    login_queue = Queue()

    monkeypatch.setattr(
        client.ui,
        "ask_username",
        lambda: "Alex",
    )

    errors = []

    monkeypatch.setattr(
        client.ui,
        "show_error",
        lambda message: errors.append(message),
    )

    stop_event = threading.Event()

    result = client.request_username(
        client_socket,
        login_queue,
        stop_event,
    )

    assert result is False
    assert errors == [
        "Failed to send username."
    ]


def test_request_username_stop_event(monkeypatch):
    client_socket = FakeSocket()
    login_queue = Queue()

    stop_event = threading.Event()
    stop_event.set()

    monkeypatch.setattr(
        client.ui,
        "ask_username",
        lambda: "Alex",
    )

    result = client.request_username(
        client_socket,
        login_queue,
        stop_event,
    )

    assert result is False
    assert client_socket.sent_data == []


# ============================================================
# chat_loop
# ============================================================

def test_chat_loop_send_message(monkeypatch):
    client_socket = FakeSocket()

    messages = iter([
        "Hello",
        "/quit",
    ])

    monkeypatch.setattr(
        client.ui,
        "prompt_message",
        lambda stop_event: next(messages),
    )

    stop_event = threading.Event()

    result = client.chat_loop(
        client_socket,
        stop_event,
    )

    assert result is True

    assert len(client_socket.sent_data) == 2

    command, payload = protocol.decode_message(
        client_socket.sent_data[0]
        .decode(config.ENCODING)
        .strip()
    )

    assert command == protocol.COMMAND_CHAT
    assert payload == "Hello"

    command, payload = protocol.decode_message(
        client_socket.sent_data[1]
        .decode(config.ENCODING)
        .strip()
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
        client.ui,
        "prompt_message",
        lambda stop_event: next(messages),
    )

    stop_event = threading.Event()

    result = client.chat_loop(
        client_socket,
        stop_event,
    )

    assert result is True
    assert len(client_socket.sent_data) == 2

    command, payload = protocol.decode_message(
        client_socket.sent_data[0]
        .decode(config.ENCODING)
        .strip()
    )

    assert command == protocol.COMMAND_ONLINE
    assert payload == ""

    command, payload = protocol.decode_message(
        client_socket.sent_data[1]
        .decode(config.ENCODING)
        .strip()
    )

    assert command == protocol.COMMAND_QUIT
    assert payload == ""


def test_chat_loop_help(monkeypatch):
    client_socket = FakeSocket()

    messages = iter([
        "/help",
        "/quit",
    ])

    monkeypatch.setattr(
        client.ui,
        "prompt_message",
        lambda stop_event: next(messages),
    )

    help_called = []

    monkeypatch.setattr(
        client.ui,
        "show_help",
        lambda: help_called.append(True),
    )

    stop_event = threading.Event()

    result = client.chat_loop(
        client_socket,
        stop_event,
    )

    assert result is True
    assert help_called == [True]

    command, payload = protocol.decode_message(
        client_socket.sent_data[-1]
        .decode(config.ENCODING)
        .strip()
    )

    assert command == protocol.COMMAND_QUIT


def test_chat_loop_empty_message(monkeypatch):
    client_socket = FakeSocket()

    messages = iter([
        "",
        "   ",
        "/quit",
    ])

    monkeypatch.setattr(
        client.ui,
        "prompt_message",
        lambda stop_event: next(messages),
    )

    stop_event = threading.Event()

    result = client.chat_loop(
        client_socket,
        stop_event,
    )

    assert result is True

    assert len(client_socket.sent_data) == 1

    command, payload = protocol.decode_message(
        client_socket.sent_data[0]
        .decode(config.ENCODING)
        .strip()
    )

    assert command == protocol.COMMAND_QUIT


def test_chat_loop_prompt_returns_none(monkeypatch):
    client_socket = FakeSocket()

    monkeypatch.setattr(
        client.ui,
        "prompt_message",
        lambda stop_event: None,
    )

    stop_event = threading.Event()

    result = client.chat_loop(
        client_socket,
        stop_event,
    )

    assert result is True
    assert stop_event.is_set()
    assert client_socket.sent_data == []


def test_chat_loop_send_failed(monkeypatch):
    class BrokenSocket(FakeSocket):
        def sendall(self, data):
            raise BrokenPipeError

    client_socket = BrokenSocket()

    monkeypatch.setattr(
        client.ui,
        "prompt_message",
        lambda stop_event: "Hello",
    )

    errors = []

    monkeypatch.setattr(
        client.ui,
        "show_error",
        lambda message: errors.append(message),
    )

    stop_event = threading.Event()

    result = client.chat_loop(
        client_socket,
        stop_event,
    )

    assert result is False
    assert stop_event.is_set()
    assert errors == [
        "Failed to send message."
    ]


def test_chat_loop_online_send_failed(monkeypatch):
    class BrokenSocket(FakeSocket):
        def sendall(self, data):
            raise BrokenPipeError

    client_socket = BrokenSocket()

    monkeypatch.setattr(
        client.ui,
        "prompt_message",
        lambda stop_event: "/online",
    )

    errors = []

    monkeypatch.setattr(
        client.ui,
        "show_error",
        lambda message: errors.append(message),
    )

    stop_event = threading.Event()

    result = client.chat_loop(
        client_socket,
        stop_event,
    )

    assert result is False
    assert stop_event.is_set()
    assert errors == [
        "Failed to request online users."
    ]


def test_chat_loop_quit_send_failed(monkeypatch):
    class BrokenSocket(FakeSocket):
        def sendall(self, data):
            raise BrokenPipeError

    client_socket = BrokenSocket()

    monkeypatch.setattr(
        client.ui,
        "prompt_message",
        lambda stop_event: "/quit",
    )

    stop_event = threading.Event()

    result = client.chat_loop(
        client_socket,
        stop_event,
    )

    assert result is False
    assert stop_event.is_set()


def test_chat_loop_keyboard_interrupt(monkeypatch):
    client_socket = FakeSocket()

    def raise_keyboard_interrupt(stop_event):
        raise KeyboardInterrupt

    monkeypatch.setattr(
        client.ui,
        "prompt_message",
        raise_keyboard_interrupt,
    )

    stop_event = threading.Event()

    result = client.chat_loop(
        client_socket,
        stop_event,
    )

    assert result is True
    assert stop_event.is_set()

    command, payload = protocol.decode_message(
        client_socket.sent_data[0]
        .decode(config.ENCODING)
        .strip()
    )

    assert command == protocol.COMMAND_QUIT
    assert payload == ""