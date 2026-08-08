import json


COMMAND_SET_NAME = "SET_NAME"
COMMAND_CHAT = "CHAT"
COMMAND_INFO = "INFO"
COMMAND_ERROR = "ERROR"
COMMAND_QUIT = "QUIT"
COMMAND_USER_LIST = "USER_LIST"
COMMAND_ONLINE = "ONLINE"
COMMAND_LOGIN_OK = "LOGIN_OK"
COMMAND_LOGIN_FAILED = "LOGIN_FAILED"
HANDLER_CLOSE = "HANDLER_CLOSE"

VALID_COMMANDS = (
    COMMAND_SET_NAME,
    COMMAND_CHAT,
    COMMAND_INFO,
    COMMAND_ERROR,
    COMMAND_QUIT,
    COMMAND_USER_LIST,
    COMMAND_ONLINE,
    COMMAND_LOGIN_OK,
    COMMAND_LOGIN_FAILED,
    HANDLER_CLOSE,
)

STATE_WAIT_USERNAME = "WAIT_USERNAME"
STATE_CHAT = "CHAT"

MESSAGE_SEPARATOR = "\n"


def encode_message(command: str, payload) -> str:
    packet = {
        "command": command,
        "payload": payload,
    }

    return json.dumps(packet, ensure_ascii=False) + MESSAGE_SEPARATOR


def decode_message(message: str) -> tuple[str | None, object | None]:
    try:
        packet = json.loads(message)

        if not isinstance(packet, dict):
            return None, None

        command = packet.get("command")
        payload = packet.get("payload")

        if command is None or payload is None:
            return None, None

        return command, payload

    except json.JSONDecodeError:
        return None, None


def is_valid_command(command: str) -> bool:
    return command in VALID_COMMANDS