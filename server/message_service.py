from server import client_registry
from shared import protocol, config


def process_message(client_socket, command, payload):
    if command == protocol.COMMAND_SET_NAME:
        return _handle_set_name(client_socket, payload)

    if command == protocol.COMMAND_CHAT:
        return _handle_chat(client_socket, payload)

    if command == protocol.COMMAND_QUIT:
        return _handle_quit(client_socket)

    if command == protocol.COMMAND_ONLINE:
        return _handle_online(client_socket)

    return False


def send_to_client(client_socket, message) -> bool:
    try:
        client_socket.sendall(message.encode(config.ENCODING))
        return True
    except (ConnectionResetError, BrokenPipeError, OSError):
        return False

def broadcast_chat(sender_socket, message):
    sender_name = client_registry.get_client_name(sender_socket)

    packet = protocol.encode_message(
        protocol.COMMAND_CHAT,
        f"{sender_name}: {message}"
    )

    _send_to_clients(packet, sender_socket)

def broadcast_info(sender_socket, message):
    packet = protocol.encode_message(
        protocol.COMMAND_INFO,
        message
    )
    _send_to_clients(packet, sender_socket)

def send_user_list(client_socket):
    users = client_registry.get_online_users()

    packet = protocol.encode_message(
        protocol.COMMAND_USER_LIST,
        users
    )

    send_to_client(client_socket, packet)

def send_info(sender_socket, message):
    packet = protocol.encode_message(
        protocol.COMMAND_INFO,
        message
    )
    return send_to_client(sender_socket, packet)

def send_error(sender_socket, message):
    packet = protocol.encode_message(
        protocol.COMMAND_ERROR,
        message
    )
    return send_to_client(sender_socket, packet)

def send_login_ok(sender_socket, message):
    packet = protocol.encode_message(
        protocol.COMMAND_LOGIN_OK,
        message
    )
    return send_to_client(sender_socket, packet)

def send_login_failed(sender_socket, message):
    packet = protocol.encode_message(
        protocol.COMMAND_LOGIN_FAILED,
        message
    )
    return send_to_client(sender_socket, packet)


def _handle_set_name(client_socket, username):
    if client_registry.get_client_state(client_socket) != protocol.STATE_WAIT_USERNAME:
        return False

    username = username.strip()

    if not username:
        send_login_failed(
            client_socket,
            "Username cannot be empty."
        )
        return False

    if not client_registry.validate_username(username):
        send_login_failed(
            client_socket,
            "Username not valid."
        )
        return False

    if not client_registry.username_available(username):
        send_login_failed(
            client_socket,
            "Username already in taken."
        )
        return False

    client_registry.set_client_name(client_socket, username)
    client_registry.set_client_state(client_socket, protocol.STATE_CHAT)

    send_login_ok(
        client_socket,
        f"Welcome, {username}!"
    )

    send_user_list(client_socket)

    broadcast_info(
        client_socket,
        f"{username} joined the chat."
    )

    return True

def _send_to_clients(packet, exclude_socket=None):
    clients = client_registry.get_all_clients()

    for client in clients:
        if client == exclude_socket:
            continue

        if not send_to_client(client, packet):
            client_registry.remove_client(client)
            client.close()

def _handle_chat(client_socket, payload):
    if client_registry.get_client_state(client_socket) != protocol.STATE_CHAT:
        return False

    payload = payload.strip()

    if not payload:
        return False

    broadcast_chat(client_socket, payload)

    return True

def _handle_quit(client_socket) -> str:
    username = client_registry.get_client_name(client_socket)
    broadcast_info(client_socket, f"{username} left the chat.")

    return protocol.HANDLER_CLOSE

def _handle_online(client_socket):
    if client_registry.get_client_state(client_socket) != protocol.STATE_CHAT:
        return False

    send_user_list(client_socket)
    return True
