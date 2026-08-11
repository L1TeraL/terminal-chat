from shared import protocol
import pytest

def test_encode_decode_message():
    packet = protocol.encode_message(
        protocol.COMMAND_CHAT,
        "Hello"
    )

    command, payload = protocol.decode_message(packet)

    assert command == protocol.COMMAND_CHAT
    assert payload == "Hello"

def test_decode_invalid_json():
    command, payload = protocol.decode_message(
        "not a json"
    )

    assert command is None
    assert payload is None

def test_decode_invalid_packet_type():
    command, payload = protocol.decode_message(
        '["CHAT", "Hello"]'
    )

    assert command is None
    assert payload is None

def test_decode_missing_command():
    command, payload = protocol.decode_message(
        '{"payload": "Hello"}'
    )

    assert command is None
    assert payload is None

def test_decode_missing_payload():
    command, payload = protocol.decode_message(
        '{"command": "CHAT"}'
    )

    assert command is None
    assert payload is None

def test_valid_command():
    assert protocol.is_valid_command(protocol.COMMAND_CHAT)

def test_invalid_command():
    assert not protocol.is_valid_command("QWERTY")