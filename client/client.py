import queue
import socket
import threading
from queue import Queue, Empty

from shared import protocol, config

HOST = config.HOST
PORT = config.PORT
BUFFER_SIZE = config.BUFFER_SIZE
ENCODING = config.ENCODING


def send_message(client_socket, message) -> bool:
    try:
        client_socket.sendall(message.encode(ENCODING))
        return True
    except (ConnectionResetError, BrokenPipeError, OSError):
        return False


def receive_messages(client_socket, stop_event, login_queue, ):
    try:
        buffer = ""

        while not stop_event.is_set():
            data = client_socket.recv(BUFFER_SIZE)

            if not data:
                print("[SERVER] Server disconnected.")
                stop_event.set()
                break

            buffer += data.decode(ENCODING)

            while protocol.MESSAGE_SEPARATOR in buffer:
                separator_index = buffer.find(protocol.MESSAGE_SEPARATOR)

                message = buffer[:separator_index]
                buffer = buffer[separator_index + 1:]

                command, payload = protocol.decode_message(
                    message,
                )

                if command is None:
                    print("[ERROR] Invalid packet received.")
                    continue

                if command == protocol.COMMAND_CHAT:
                    print(payload)

                elif command == protocol.COMMAND_LOGIN_OK:
                    login_queue.put(
                        (
                            True,
                            ""
                        )
                    )

                elif command == protocol.COMMAND_LOGIN_FAILED:
                    login_queue.put(
                        (
                            False,
                            payload
                        )
                    )

                elif command == protocol.COMMAND_INFO:
                    print(f"[SERVER] {payload}")

                elif command == protocol.COMMAND_ERROR:
                    print(f"[ERROR] {payload}")

                elif command == protocol.COMMAND_USER_LIST:
                    print(f"[SERVER] Online {len(payload)}")

                    for user in payload:
                        print(f"         - {user}")

                else:
                    print(f"[ERROR] Unknown command: {command}")


    except (ConnectionResetError, OSError):
        if not stop_event.is_set():
            print("[SERVER] Connection lost.")

        stop_event.set()


def request_username(client_socket, login_queue, stop_event):
    while True:
        username = input("Enter username: ").strip()

        if stop_event.is_set():
            return False

        if not username:
            print("[SERVER] Username cannot be empty.")
            continue

        packet = protocol.encode_message(
            protocol.COMMAND_SET_NAME,
            username,
        )

        if not send_message(client_socket, packet):
            print("[SERVER] Failed to send username.")
            return False

        while not stop_event.is_set():
            try:
                success, message = login_queue.get(timeout=1)

                if success:
                    return True

                print(f"[ERROR] {message}")
                break

            except Empty:
                continue

    return False


def chat_loop(client_socket, stop_event):
    try:
        while not stop_event.is_set():
            message = input().strip()

            if not message:
                continue

            if message.lower() == "/online":
                packet = protocol.encode_message(
                    protocol.COMMAND_ONLINE,
                    ""
                )

                if not send_message(client_socket, packet):
                    stop_event.set()
                    return False

                continue

            if message.lower() == "/quit":
                packet = protocol.encode_message(
                    protocol.COMMAND_QUIT,
                    ""
                )

                if not send_message(client_socket, packet):
                    stop_event.set()
                    return False
                break

            packet = protocol.encode_message(
                protocol.COMMAND_CHAT,
                message,
            )

            if not send_message(client_socket, packet):
                print("[SERVER] Failed to send message.")
                stop_event.set()
                break

    except KeyboardInterrupt:
        packet = protocol.encode_message(
            protocol.COMMAND_QUIT,
            ""
        )

        send_message(client_socket, packet)
        stop_event.set()

        return False

def main():
    stop_event = threading.Event()
    login_queue = Queue()

    client_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    receiver_thread = None

    try:
        client_socket.connect((HOST, PORT))

        receiver_thread = threading.Thread(
            target=receive_messages,
            args=(client_socket, stop_event, login_queue),
        )
        receiver_thread.start()

        print("[SERVER] Connected.")

        if not request_username(client_socket, login_queue, stop_event):
            return

        if not chat_loop(client_socket, stop_event):
            return

    except ConnectionRefusedError:
        print("[SERVER] Connection refused.")


    finally:
        stop_event.set()

        try:
            client_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

        client_socket.close()

        if receiver_thread is not None:
            receiver_thread.join()


if __name__ == "__main__":
    main()