import os
import socket


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


def prepare_upload() -> tuple[str, bytes]:
    """file_path, headerを取得して返す"""

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
            continue

        break

    return file_path, header


def run_tcp_client(
        file_path: str,
        header: bytes
) -> None:

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect(SERVER_ADDRESS)

        client_socket.sendall(header)

        with open(file_path, "rb") as f:
            while True:
                contents = f.read(CHUNK_SIZE)

                if not contents:
                    print("データの送信が完了しました。\n")
                    break

                client_socket.sendall(contents)
                print("データを送信中です....")

        data = recv_exact(
            sock=client_socket,
            target_size=RESPONSE_SIZE
        )

        status_code = decode_response(data)

        if status_code == StatusCode.SUCCESS:
            print("サーバーへのアップロードが完了しました。\n")
        elif status_code == StatusCode.INCOMPLETE_UPLOAD:
            print("サーバーへのアップロードに失敗しました。\n")
        elif status_code == StatusCode.SERVER_ERROR:
            print("SERVER ERROR")
        elif status_code == StatusCode.STORAGE_LIMIT_EXCEEDED:
            print("サーバー側の容量不足によりアップロード出来ません。\n")


def main() -> None:

    while True:
        try:
            file_path, header = prepare_upload()

            run_tcp_client(
                file_path=file_path,
                header=header
            )

        except ConnectionRefusedError:
            print("サーバーに接続できませんでした。")

        except ConnectionError as e:
            print(f"通信エラー: {e}")

        except OSError as e:
            print(f"エラーが発生しました: {e}")

        except KeyboardInterrupt:
            print("アプリを終了します。")
            break


if __name__ == "__main__":
    main()