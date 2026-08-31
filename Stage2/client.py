import socket
import time

from pathlib import Path


from transport import(
    send_mmp_message,
    recv_mmp_message
)


SERVER_ADDRESS = ("127.0.0.1", 9001)

DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


def check_job_status(job_id: str) -> tuple[dict, Path | None]:
    """動画の処理状況をサーバーに確認する"""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect(SERVER_ADDRESS)

        request = {
            "operation" : "check_status",
            "job_id" : job_id
        }

        send_mmp_message(
            connection=client_socket,
            json_data=request,
            media_type=None,
            payload=None
        )

        json_data, _, saved_path = recv_mmp_message(
            connection=client_socket,
            save_dir=DOWNLOAD_DIR
        )

        return json_data, saved_path


def poll_job(job_id: str) -> None:

    while True:
        time.sleep(60)

        json_data, saved_path = check_job_status(job_id)

        status = json_data["status"]

        if status == "completed":
            print(
                "動画処理が完了しました。\n"
                f"保存場所: {saved_path}\n"
            )     
            break
        elif status == "processing":
            print("動画を処理中です。しばらくお待ちください。\n")
        elif status == "failed":
            print(
                "動画処理に失敗しました。\n"
                f"原因:{json_data['description']}\n"
                f"解決方法:{json_data['solution']}\n"
            )
            break
        else:
            raise ValueError(f"不明なJOBステータスです:{status}")


while True:
    file_path = Path(
        input(
            "アップロードする動画ファイルのパスを入力してください。\n"
            "> "
        ).strip()
    )

    if not file_path.is_file():
        print("存在しないファイルです。\n")
        continue

    break

while True:
    operation = input(
        "動画に対する操作を以下から選び入力してください。\n"
        "compress, resize, change_aspect_ratio, extract_audio, create_clip\n"
        "> "
    ).strip()

    if operation not in {"compress", "resize", "change_aspect_ratio", "extract_audio", "create_clip"}:
        print("対応していない操作です。")
        continue

    if operation == "resize":
        while True:
            try:
                width = int(input(
                    "横幅の解像度(px)を入力してください。\n"
                    "> "
                ))
            except ValueError:
                print("入力値が不正です。\n")
                continue

            break

        while True:
            try:
                height = int(input(
                    "縦幅の解像度(px)を入力してください。\n"
                    "> "
                ))
            except ValueError:
                print("入力値が不正です。\n")
                continue

            break

        params = {
            "width" : width,
            "height" : height
        }

    elif operation == "change_aspect_ratio":
        while True:
            try:
                aspect_width = int(input(
                    "横のアスペクト比を入力してください。\n"
                    "> "
                ))
            except ValueError:
                print("入力値が不正です。\n")
                continue

            break

        while True:
            try:
                aspect_height = int(input(
                    "縦のアスペクト比を入力してください。\n"
                    "> "
                ))
            except ValueError:
                print("入力値が不正です。\n")
                continue

            break

        params = {
            "aspect_width" : aspect_width,
            "aspect_height" : aspect_height
        }

    elif operation == "create_clip":
        while True:
            try: 
                start_time = float(input(
                    "クリップの開始時間(秒)を入力してください。\n"
                    "> "
                ))
            except ValueError:
                print("入力値が不正です。\n")
                continue

            break

        while True:
            try:
                end_time = float(input(
                    "クリップの終了時間(秒)を入力してください。\n"
                    ">"
                ))
            except ValueError:
                print("入力値が不正です。\n")
                continue

            break

        while True:
            output_format = input(
                "出力形式を以下から選び入力してください。\n"
                "・gif\n"
                "・webm\n"
                "> "
            ).strip().lower()

            if output_format not in {"gif", "webm"}:
                print("対応していない出力形式です。\n")
                continue

            break

        params = {
            "start_time" : start_time,
            "end_time" : end_time,
            "output_format" : output_format
        }

    else:
        params = {}

    break

job_id: str | None = None

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    client_socket.connect(SERVER_ADDRESS)

    media_type = file_path.suffix.removeprefix(".").lower()

    json_data = {
        "operation" : operation,
        "params" : params
    }

    send_mmp_message(
        connection=client_socket,
        json_data=json_data,
        media_type=media_type,
        payload=file_path
    )

    received_json_data, _, _ = recv_mmp_message(
        connection=client_socket,
        save_dir=DOWNLOAD_DIR
    )

    if received_json_data["status"] == "processing":
        job_id = received_json_data["job_id"]

        print(
            "動画処理を開始します。\n"
            f"ID:{job_id}\n"
        )

    elif received_json_data["status"] == "failed":
        print(
            "動画処理に失敗しました。\n"
            f"エラー内容:{received_json_data['description']}\n"
            f"解決方法: {received_json_data['solution']}\n"
        )

if job_id is not None:
    poll_job(job_id)