import socket


from transport import(
    recv_mmp_message,
    send_mmp_message
)


SERVER_PORT = 9001
SERVER_ADDRESS = "0.0.0.0"


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((SERVER_ADDRESS, SERVER_PORT))

    server_socket.listen(1)

    while True:
        connection, client_address = server_socket.accept()

        with connection:
            json_data, media_type, payload = recv_mmp_message(connection)


            print(json_data["operation"])
            print(media_type)
            print(payload)