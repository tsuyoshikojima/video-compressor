import socket

from pathlib import Path


from transport import(
    send_mmp_message,
)


SERVER_ADDRESS = ("127.0.0.1", 9001)


while True:
    file_path = Path(
        input(
            "アップロードするファイルを入力してください。\n"
            "> "
        ).strip()
    )

    if not file_path.is_file():
        print("\n存在しないファイルです。")
        continue

    break


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    client_socket.connect(SERVER_ADDRESS)

    json = {"operation" : "test"}

    media_type = file_path.suffix.replace(".", "").lower()

    send_mmp_message(
        connection=client_socket,
        json_data=json,
        media_type=media_type,
        payload=file_path
    )