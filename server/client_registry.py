import threading

from shared import protocol

clients = {}
clients_lock = threading.Lock()


def add_client(client_socket, client_address):
    with clients_lock:
        clients[client_socket] = {
            "address": client_address,
            "name": None,
            "state": protocol.STATE_WAIT_USERNAME,
        }


def remove_client(client_socket):
    with clients_lock:
        client = clients.pop(client_socket, None)

        if client is None:
            return "anonymous"

        return client.get("name") or "anonymous"


def get_all_clients():
    with clients_lock:
        return list(clients.keys())


def get_client_state(client_socket):
    with clients_lock:
        client = clients.get(client_socket)

        if client is None:
            return None

        return client["state"]


def set_client_state(client_socket, state):
    with clients_lock:
        client = clients.get(client_socket)

        if client is None:
            return False

        client["state"] = state
        return True


def get_client_name(client_socket):
    with clients_lock:
        client = clients.get(client_socket)

        if client is None:
            return None

        return client["name"]


def set_client_name(client_socket, name):
    with clients_lock:
        client = clients.get(client_socket)

        if client is None:
            return False

        client["name"] = name
        return True


def get_client_address(client_socket):
    with clients_lock:
        client = clients.get(client_socket)

        if client is None:
            return None

        return client["address"]


def username_available(username):
    with clients_lock:
        return all(
            client.get("name") != username
            for client in clients.values()
        )


def validate_username(username):
    RESERVED_NAMES = {
        "SERVER",
        "INFO",
        "ERROR",
        "None",
    }

    username = username.strip()

    if len(username) < 3:
        return False

    if username.upper() in RESERVED_NAMES or username in RESERVED_NAMES:
        return False

    if username.startswith("[") and username.endswith("]"):
        return False

    return True

def get_online_users() -> list:
    with clients_lock:
        return  [
            client["name"]
            for client in clients.values()
            if client["name"] is not None
        ]
