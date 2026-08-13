import os
import socket
import sys


from protocol import(
    decode_response,
    encode_file_size,
    RESPONSE_SIZE,
    StatusCode
)


SERVER_ADDRESS = ("127.0.0.1", 9001)
CHUNK_SIZE = 1400


def recv_exact(
        sock: socket.socket,
        target_size: int
) -> bytes:

    output = bytearray()

    while target_size > len(output):
        remaining_size = target_size - len(output)

        chunk = sock.recv(remaining_size)

        if not chunk:
            raise ConnectionError("接続が途中で切断されました。")

        output += chunk

    return bytes(output)

try:
    while True:
        file_path = input(
            "サーバーにアップロードするmp4ファイルのパスを入力してください。\n"
            "> "
        ).strip()

        if not os.path.isfile(file_path):
            print("ファイルが存在しません。\n")
            continue

        if not file_path.lower().endswith(".mp4"):
            print("mp4ファイル以外はアップロード出来ません。\n")
            continue

        file_size = os.path.getsize(file_path)

        try:
            header = encode_file_size(file_size)
        except ValueError:
            print("ファイルのサイズが不正です。")
            sys.exit(1)

        break
except KeyboardInterrupt:
    print("アプリを終了します。")

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect(SERVER_ADDRESS)

        client_socket.sendall(header)


        with open(file_path, "rb") as f:
            while True:
                contents = f.read(CHUNK_SIZE)

                if not contents:
                    break

                client_socket.sendall(contents)

        data = recv_exact(
            sock=client_socket,
            target_size=RESPONSE_SIZE
        )

        status_code = decode_response(data)

        if status_code == StatusCode.SUCCESS:
            print("アップロードが完了しました。")
        elif status_code == StatusCode.INCOMPLETE_UPLOAD:
            print("アップロードに失敗しました。")
        elif status_code == StatusCode.SERVER_ERROR:
            print("SERVER ERROR")

except ConnectionRefusedError:
    print("サーバーに接続できませんでした。")

except ConnectionError as e:
    print(f"通信エラー: {e}")

except OSError as e:
    print(f"エラーが発生しました: {e}")

except KeyboardInterrupt:
    print("アプリを終了します。")

