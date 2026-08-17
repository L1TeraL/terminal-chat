import socket
import threading
import time

import pytest

from server import server
from shared import protocol, config


@pytest.fixture
def running_server():
    stop_event = threading.Event()

    thread = threading.Thread(
        target=server.main,
        args=("127.0.0.1", 5051, stop_event),
        daemon=True,
    )

    thread.start()

    time.sleep(0.1)

    yield

    stop_event.set()
    thread.join(timeout=1)

class SocketReader:
    def __init__(self, socket):
        self.socket = socket
        self.buffer = ""

    def recv_message(self):
        while protocol.MESSAGE_SEPARATOR not in self.buffer:
            data = self.socket.recv(config.BUFFER_SIZE)

            if not data:
                return None, None

            self.buffer += data.decode(config.ENCODING)

        separator_index = self.buffer.find(
            protocol.MESSAGE_SEPARATOR
        )

        message = self.buffer[:separator_index]

        self.buffer = self.buffer[
            separator_index + 1:
        ]

        return protocol.decode_message(message)

def test_server_accepts_connections(running_server):
    client = socket.create_connection(('127.0.0.1', 5051))

    client.close()

def test_server_login(running_server):
    client = socket.create_connection(('127.0.0.1', 5051))

    packet = protocol.encode_message(
        protocol.COMMAND_SET_NAME,
        'Alex'
    )

    client.sendall(packet.encode(config.ENCODING))

    data = client.recv(config.BUFFER_SIZE)

    command, payload = protocol.decode_message(
        data.decode(config.ENCODING).strip()
    )

    assert command == protocol.COMMAND_LOGIN_OK
    assert payload == 'Welcome, Alex!'

    client.close()

def test_two_clients_login(running_server):
    client_1 = socket.create_connection(
        ("127.0.0.1", 5051)
    )
    client_2 = socket.create_connection(
        ("127.0.0.1", 5051)
    )

    reader_1 = SocketReader(client_1)
    reader_2 = SocketReader(client_2)

    # Alex login
    packet = protocol.encode_message(
        protocol.COMMAND_SET_NAME,
        "Alex",
    )

    client_1.sendall(
        packet.encode(config.ENCODING)
    )

    command, payload = reader_1.recv_message()

    assert command == protocol.COMMAND_LOGIN_OK
    assert payload == "Welcome, Alex!"

    command, payload = reader_1.recv_message()

    assert command == protocol.COMMAND_CHAT_HISTORY
    assert isinstance(payload, list)

    command, payload = reader_1.recv_message()

    assert command == protocol.COMMAND_USER_LIST
    assert payload == ["Alex"]

    command, payload = reader_2.recv_message()

    assert command == protocol.COMMAND_INFO
    assert payload == "Alex joined the chat."

    # Bob login
    packet = protocol.encode_message(
        protocol.COMMAND_SET_NAME,
        "Bob",
    )

    client_2.sendall(
        packet.encode(config.ENCODING)
    )

    command, payload = reader_2.recv_message()

    assert command == protocol.COMMAND_LOGIN_OK
    assert payload == "Welcome, Bob!"

    command, payload = reader_2.recv_message()

    assert command == protocol.COMMAND_CHAT_HISTORY
    assert isinstance(payload, list)

    command, payload = reader_2.recv_message()

    assert command == protocol.COMMAND_USER_LIST
    assert payload == ["Alex", "Bob"]

    packet = protocol.encode_message(
        protocol.COMMAND_QUIT,
        "",
    )

    client_1.sendall(
        packet.encode(config.ENCODING)
    )

    command, payload = reader_2.recv_message()

    assert command == protocol.COMMAND_INFO
    assert payload == "Alex left the chat."

    client_1.close()
    client_2.close()