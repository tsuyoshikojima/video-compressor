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

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)     # uploadsディレクトリを作成

MAX_STORAGE_SIZE = 4 * 1024 ** 4  # 4TiB


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


def get_total_uploaded_size() -> int:
    """ディレクトリ内にアップロードしたファイルのデータの総量(バイト)を取得する"""

    total_size = 0

    for file_path in UPLOAD_DIR.iterdir():  # ディレクトリ内のパスを一つずつ取り出す
        if file_path.is_file() and file_path.suffix == ".mp4":  # 拡張子が.mp4のファイル
            total_size += file_path.stat().st_size  # ファイルのバイト単位でのサイズ

    print(
        f"{total_size}バイトのデータを保存しています。"
        f"ストレージの残りの容量は{MAX_STORAGE_SIZE - total_size}です。"
    )

    return total_size


def remove_temp_files() -> None:
    """ストレージに.tempファイルがないか確認し削除する"""

    for file_path in UPLOAD_DIR.iterdir():
        if file_path.suffix == ".temp" and file_path.is_file():   # .tempファイルが残っていたら削除する
            file_path.unlink()
            print(f"{file_path.name}を削除しました。")


try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((SERVER_ADDRESS,SERVER_PORT))
        print("サーバーを起動します。")

        remove_temp_files()

        server_socket.listen(1)

        while True:
            connection, client_address = server_socket.accept()

            file_id = uuid.uuid4().hex      # 32文字の小文字16進数文字列でのUUID。クライアントからファイル名が送られないのでuuidで管理

            temp_path = UPLOAD_DIR / f"{file_id}.temp"  # 異常終了した場合に、どのファイルが完全なものか分からないので仮のファイルに保存
            saved_path = UPLOAD_DIR / f"{file_id}.mp4"  # ダウンロードが完了したら、正式なファイル名に変更

            with connection:
                try:
                    header = recv_exact(
                        connection=connection,
                        target_size=HEADER_LENGTH
                    )

                    file_size = decode_file_size(header=header)
                    remaining_size = file_size

                    total_uploaded_size = get_total_uploaded_size()     # サーバーに保存しているファイルの総データ量を取得

                    if total_uploaded_size + file_size > MAX_STORAGE_SIZE:
                        print("サーバーのストレージ容量が足りません。")

                        while remaining_size > 0:
                            data = connection.recv(
                                min(remaining_size, CHUNK_SIZE)
                            )

                            if not data:
                                raise ConnectionError("データ受信中に切断されました。")

                            remaining_size -= len(data)
                        

                        connection.sendall(encode_response(StatusCode.STORAGE_LIMIT_EXCEEDED))

                        continue

                    with open(temp_path, "wb") as f:
                        # ファイルを生成し、データを書き込む
                        while remaining_size > 0:
                            data = connection.recv(
                                min(CHUNK_SIZE, remaining_size)
                            )

                            if not data:
                                raise ConnectionError("データ受信中に切断されました。")

                            f.write(data)

                            remaining_size -= len(data)

                    temp_path.rename(saved_path)
                    print(f"{file_size}バイトの{saved_path}のアップロードを完了しました。")

                    response = encode_response(StatusCode.SUCCESS)
                    connection.sendall(response)

                except ConnectionError:
                    print("アップロード中にクライアントとの接続が切断されました。")

                    if temp_path.exists():
                        temp_path.unlink()


except KeyboardInterrupt:
    print("サーバーを停止します。")