import socket
import threading

from server import client_registry
from server.message_service import process_message
from shared import protocol, config


HOST = config.HOST
PORT = config.PORT
BUFFER_SIZE = config.BUFFER_SIZE
ENCODING = config.ENCODING


def handle_client(client_socket):
    try:
        buffer = ""
        should_close = False

        while not should_close:
            data = client_socket.recv(BUFFER_SIZE)

            if not data:
                print("[INFO] Client disconnected.")
                break

            buffer += data.decode(ENCODING)

            while protocol.MESSAGE_SEPARATOR in buffer:
                separator_index = buffer.find(protocol.MESSAGE_SEPARATOR)

                message = buffer[:separator_index]
                buffer = buffer[separator_index + 1:]

                command, payload = protocol.decode_message(message)

                if command is None:
                    print("[INFO] Invalid packet received.")
                    continue

                if not protocol.is_valid_command(command):
                    print(f"[INFO] Unknown command: {command}")
                    continue

                if process_message(client_socket, command, payload) == protocol.HANDLER_CLOSE:
                    should_close = True
                    break



    except ConnectionResetError:
        print("[INFO] Client connection reset.")

    except OSError:
        print("[INFO] Socket closed.")

    finally:
        removed_name = client_registry.remove_client(client_socket)

        print(f"[INFO] Client '{removed_name}' disconnected.")

        client_socket.close()


def main(host=HOST, port=PORT, stop_event=None):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )

    server_socket.bind((host, port))
    server_socket.listen()
    server_socket.settimeout(0.2)

    print(f"[SERVER] Listening on {host}:{port}")

    try:
        while stop_event is None or not stop_event.is_set():
            try:
                client_socket, client_address = server_socket.accept()
            except socket.timeout:
                continue

            print(f"[SERVER] New connection: {client_address}")

            client_registry.add_client(
                client_socket,
                client_address,
            )

            threading.Thread(
                target=handle_client,
                args=(client_socket,),
            ).start()

    except KeyboardInterrupt:
        print("\n[SERVER] Shutdown requested.")

    finally:
        server_socket.close()
        print("[SERVER] Server stopped.")


if __name__ == "__main__":
    main()