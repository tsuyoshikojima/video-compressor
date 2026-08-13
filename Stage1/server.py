import socket
import uuid
from pathlib import Path


from protocol import(
    decode_file_size,
    encode_response,
    HEADER_LENGTH,
    StatusCode
)


SERVER_PORT = 9001
SERVER_ADDRESS = "0.0.0.0"

CHUNK_SIZE = 1400

UPLOAD_DIR = Path(__file__).parent/"uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def recv_exact(
        connection: socket.socket,
        target_size: int
) -> bytes:

    output = bytearray()

    while len(output) < target_size:
        remaining_size = target_size - len(output)

        chunk = connection.recv(remaining_size)

        if not chunk:
            raise ConnectionError("接続が途中で切断されました。")

        output += chunk

    return bytes(output)


try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((SERVER_ADDRESS,SERVER_PORT))
        print("サーバーを起動します。")

        server_socket.listen(1)

        while True:
            connection, client_address = server_socket.accept()

            file_id = uuid.uuid4().hex      # 32文字の小文字16進数文字列でのUUID
            saved_path = UPLOAD_DIR / f"{file_id}.mp4"
            temp_path = UPLOAD_DIR / f"{file_id}.temp"

            with connection:
                try:
                    header = recv_exact(
                        connection=connection,
                        target_size=HEADER_LENGTH
                    )

                    file_size = decode_file_size(header=header)

                    remaining_size = file_size

                    with open(temp_path, "wb") as f:
                        while remaining_size > 0:
                            data = connection.recv(
                                min(CHUNK_SIZE, remaining_size)
                            )

                            if not data:
                                raise ConnectionError("データ受信中に切断されました。")

                            f.write(data)

                            remaining_size -= len(data)

                    temp_path.rename(saved_path)

                    print(f"{saved_path}のアップロードを完了しました。")

                    response = encode_response(StatusCode.SUCCESS)

                    connection.sendall(response)

                except ConnectionError:
                    print("アップロード中にクライアントとの接続が切断されました。")

                    if temp_path.exists():
                        temp_path.unlink()


except KeyboardInterrupt:
    print("サーバーを停止します。")