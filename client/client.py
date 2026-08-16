import socket
import threading
from queue import Empty, Queue

from client.ui import ui
from shared import config, protocol


HOST = config.HOST
PORT = config.PORT
BUFFER_SIZE = config.BUFFER_SIZE
ENCODING = config.ENCODING


def send_message(client_socket, message) -> bool:
    try:
        client_socket.sendall(
            message.encode(ENCODING)
        )
        return True

    except (
        ConnectionResetError,
        BrokenPipeError,
        OSError,
    ):
        return False


def receive_messages(
    client_socket,
    stop_event,
    login_queue,
    history_queue,
):
    buffer = ""

    try:
        while not stop_event.is_set():
            data = client_socket.recv(BUFFER_SIZE)

            if not data:
                ui.show_info(
                    "Server disconnected."
                )

                stop_event.set()
                break

            buffer += data.decode(ENCODING)

            while protocol.MESSAGE_SEPARATOR in buffer:
                separator_index = buffer.find(
                    protocol.MESSAGE_SEPARATOR
                )

                message = buffer[:separator_index]

                buffer = buffer[
                    separator_index + 1:
                ]

                command, payload = protocol.decode_message(
                    message
                )

                if command is None:
                    ui.show_error(
                        "Invalid packet received."
                    )
                    continue

                if command == protocol.COMMAND_CHAT:
                    ui.show_chat_message(payload)

                elif command == protocol.COMMAND_LOGIN_OK:
                    login_queue.put(
                        (
                            True,
                            payload,
                        )
                    )

                elif command == protocol.COMMAND_LOGIN_FAILED:
                    login_queue.put(
                        (
                            False,
                            payload,
                        )
                    )

                elif command == protocol.COMMAND_INFO:
                    ui.show_info(payload)

                elif command == protocol.COMMAND_ERROR:
                    ui.show_error(payload)

                elif command == protocol.COMMAND_USER_LIST:
                    ui.show_users(payload)

                elif command == protocol.COMMAND_CHAT_HISTORY:
                    history_queue.put(payload)

                else:
                    ui.show_error(
                        f"Unknown command: {command}"
                    )

    except (
        ConnectionResetError,
        OSError,
    ):
        if not stop_event.is_set():
            ui.show_error(
                "Connection lost."
            )

        stop_event.set()


def request_username(
    client_socket,
    login_queue,
    stop_event,
):
    while not stop_event.is_set():
        username = ui.ask_username()

        if not username:
            ui.show_error(
                "Username cannot be empty."
            )
            continue

        packet = protocol.encode_message(
            protocol.COMMAND_SET_NAME,
            username,
        )

        if not send_message(
            client_socket,
            packet,
        ):
            ui.show_error(
                "Failed to send username."
            )
            return False

        while not stop_event.is_set():
            try:
                success, message = login_queue.get(
                    timeout=1
                )

                if success:
                    ui.show_login_success(username)
                    return True

                ui.show_login_failed(message)
                break

            except Empty:
                continue

    return False


def chat_loop(
    client_socket,
    stop_event,
):
    try:
        while not stop_event.is_set():
            message = ui.prompt_message(
                stop_event
            )

            if message is None:
                break

            if not message:
                continue

            command = message.lower()

            if command == "/online":
                packet = protocol.encode_message(
                    protocol.COMMAND_ONLINE,
                    "",
                )

                if not send_message(
                    client_socket,
                    packet,
                ):
                    ui.show_error(
                        "Failed to request online users."
                    )

                    stop_event.set()
                    return False

                continue

            if command == "/help":
                ui.show_help()
                continue

            if command == "/quit":
                packet = protocol.encode_message(
                    protocol.COMMAND_QUIT,
                    "",
                )

                if not send_message(
                    client_socket,
                    packet,
                ):
                    stop_event.set()
                    return False

                break

            packet = protocol.encode_message(
                protocol.COMMAND_CHAT,
                message,
            )

            if not send_message(
                client_socket,
                packet,
            ):
                ui.show_error(
                    "Failed to send message."
                )

                stop_event.set()
                return False

    except KeyboardInterrupt:
        packet = protocol.encode_message(
            protocol.COMMAND_QUIT,
            "",
        )

        send_message(
            client_socket,
            packet,
        )

    finally:
        stop_event.set()

    return True


def main():
    stop_event = threading.Event()
    login_queue = Queue()
    history_queue = Queue()

    client_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    receiver_thread = None

    try:
        client_socket.connect(
            (HOST, PORT)
        )

        ui.show_welcome()
        ui.show_connected()

        receiver_thread = threading.Thread(
            target=receive_messages,
            args=(
                client_socket,
                stop_event,
                login_queue,
                history_queue,
            ),
            daemon=True,
        )

        receiver_thread.start()

        if not request_username(
            client_socket,
            login_queue,
            stop_event,
        ):
            return

        try:
            history = history_queue.get(timeout=1)
        except Empty:
            history = []

        ui.show_chat_history(history)

        chat_loop(
            client_socket,
            stop_event,
        )

    except ConnectionRefusedError:
        ui.show_error(
            "Connection refused."
        )

    except KeyboardInterrupt:
        stop_event.set()

    finally:
        stop_event.set()

        try:
            client_socket.shutdown(
                socket.SHUT_RDWR
            )
        except OSError:
            pass

        client_socket.close()

        if receiver_thread is not None:
            receiver_thread.join(
                timeout=1
            )

        ui.show_goodbye()


if __name__ == "__main__":
    main()