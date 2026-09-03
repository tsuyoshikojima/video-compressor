import socket

from concurrent.futures import ThreadPoolExecutor   # スレッドのプールを使用して非同期に呼び出しを行う、Executorのサブクラス
from pathlib import Path


from transport import(
    recv_mmp_message,
    send_mmp_message
)


from job_manager import(
    JobManager
)


from request_processor import(
    create_output_path,
    process_job
)


SERVER_PORT = 9001
SERVER_ADDRESS = "0.0.0.0"

SERVER_UPLOAD_DIR = Path(__file__).parent / "uploads"
SERVER_UPLOAD_DIR.mkdir(exist_ok=True)


manager = JobManager()

executor = ThreadPoolExecutor(max_workers=4)    # FFMPEGの同時実行数を最大４つに制限する

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((SERVER_ADDRESS, SERVER_PORT))
        print("サーバーを起動します。")
        server_socket.listen(1)

        while True:
            connection, client_address = server_socket.accept()

            with connection:
                try:
                    json_data, media_type, saved_path = recv_mmp_message(
                        connection=connection,
                        save_dir=SERVER_UPLOAD_DIR
                    )
                except (ConnectionError, ValueError) as error:
                    print(f"MMPメッセージの受信に失敗しました。:{error}")
                    continue

                operation = json_data.get("operation")

                if operation is None:
                    if saved_path is not None:
                        saved_path.unlink(missing_ok=True)

                    response = {
                        "status" : "failed",
                        "error_code" : "INVALID_REQUEST",
                        "description" : "operationが指定されていません。",
                        "solution" : "operationを指定してください。"
                    }

                    send_mmp_message(
                        connection=connection,
                        json_data=response,
                        media_type=None,
                        payload=None
                    )

                    continue

                # ポーリング
                if operation == "check_status":
                    if saved_path is not None:
                        saved_path.unlink(missing_ok=True)

                        response = {
                            "status" : "failed",
                            "error_code" : "INVALID_REQUEST",
                            "description" : "check_statusにはファイルを指定できません。",
                            "solution" : "job_idのみ指定してください。"
                        }

                        send_mmp_message(
                            connection=connection,
                            json_data=response,
                            media_type=None,
                            payload=None
                        )

                        continue

                    job_id = json_data.get("job_id")

                    if job_id is None:
                        response = {
                            "status" : "failed",
                            "error_code" : "INVALID_REQUEST",
                            "description" : "job_idが指定されていません。",
                            "solution" : "確認するJobのjob_idを指定してください。"
                        }

                        send_mmp_message(
                            connection=connection,
                            json_data=response,
                            media_type=None,
                            payload=None
                        )

                        continue

                    job = manager.get_job(job_id)

                    if job is None:
                        response = {
                            "status" : "failed",
                            "error_code" : "JOB_NOT_FOUND",
                            "description" : "指定されたjob_idが存在しません。",
                            "solution" : "job_idを確認してください。"
                        }

                        send_mmp_message(
                            connection=connection,
                            json_data=response,
                            media_type=None,
                            payload=None
                        )

                    elif job.client_ip != client_address[0]:
                        response = {
                            "status" : "failed",
                            "error_code" : "JOB_ACCESS_DENIED",
                            "description" : "このJOBにアクセスできません。",
                            "solution" : "JOBを作成したクライアントから確認してください。"
                        }

                        send_mmp_message(
                            connection=connection,
                            json_data=response,
                            media_type=None,
                            payload=None
                        )

                    elif job.status == "processing":
                        response = {
                            "status" : "processing",
                            "job_id" : job.job_id
                        }

                        send_mmp_message(
                            connection=connection,
                            json_data=response,
                            media_type=None,
                            payload=None
                        )

                    elif job.status == "completed":
                        response = {
                            "status" : "completed",
                            "job_id" : job.job_id
                        }

                        send_mmp_message(
                            connection=connection,
                            json_data=response,
                            media_type=job.output_path.suffix.removeprefix("."),
                            payload=job.output_path
                        )

                        job.input_path.unlink(missing_ok=True)
                        job.output_path.unlink(missing_ok=True)
                        manager.remove_job(job_id)

                    elif job.status == "failed":
                        response = {
                            "job_id" : job.job_id,
                            "status" : "failed",
                            "error_code" : "PROCESSING_FAILED",
                            "description" : job.error,
                            "solution" : "入力ファイルとパラメータを確認してください。"
                        }

                        send_mmp_message(
                            connection=connection,
                            json_data=response,
                            media_type=None,
                            payload=None
                        )

                        job.input_path.unlink(missing_ok=True)
                        job.output_path.unlink(missing_ok=True)
                        manager.remove_job(job_id)

                # JOBを作成し、動画処理を別スレッドで実行
                else:
                    if saved_path is None:
                        # operationが動画処理なのにペイロードがない場合、エラーを返す。
                        response = {
                            "status" : "failed",
                            "error_code" : "PAYLOAD_REQUIRED",
                            "description" : "動画ファイルが指定されていません。",
                            "solution" : "処理する動画ファイルを送信してください。"
                        }

                        send_mmp_message(
                            connection=connection,
                            json_data=response,
                            media_type=None,
                            payload=None
                        )

                        continue

                    params = json_data.get("params")

                    if params is None:
                        saved_path.unlink(missing_ok=True)

                        response = {
                            "status" : "failed",
                            "error_code" : "INVALID_REQUEST",
                            "description" : "paramsが指定されていません。",
                            "solution" : "paramsを指定してください。"
                        }

                        send_mmp_message(
                            connection=connection,
                            json_data=response,
                            media_type=None,
                            payload=None
                        )

                        continue

                    if not isinstance(params, dict):
                        saved_path.unlink(missing_ok=True)

                        response = {
                            "status" : "failed",
                            "error_code" : "INVALID_REQUEST",
                            "description" : "paramsの形式が不正です",
                            "solution" : "paramsをJSONオブジェクトで指定してください。"
                        }

                        send_mmp_message(
                            connection=connection,
                            json_data=response,
                            media_type=None,
                            payload=None
                        )

                        continue

                    if manager.has_active_job(client_address[0]):
                        saved_path.unlink(missing_ok=True)

                        response = {
                            "status" : "failed",
                            "error_code" : "JOB_ALREADY_PROCESSING",
                            "description" : "このIPアドレスでは既に動画を処理しています。",
                            "solution" : "現在の処理が完了してから再度実行してください。"
                        }

                        send_mmp_message(
                            connection=connection,
                            json_data=response,
                            media_type=None,
                            payload=None
                        )

                    else:
                        assert media_type is not None

                        try:
                            output_path = create_output_path(
                                operation=operation,
                                media_type=media_type,
                                params=params
                            )
                        except (ValueError, KeyError) as error:
                            saved_path.unlink(missing_ok=True)

                            response = {
                                "status" : "failed",
                                "error_code" : "INVALID_REQUEST",
                                "description" : f"{error}",
                                "solution" : "operation,params,出力形式を確認してください。"
                            }

                            send_mmp_message(
                                connection=connection,
                                json_data=response,
                                media_type=None,
                                payload=None
                            )

                            continue

                        job = manager.create_job(
                            client_ip=client_address[0],
                            operation=operation,
                            input_path=saved_path,
                            output_path=output_path,
                            params=params
                        )

                        executor.submit(
                            process_job,
                            job=job,
                            job_manager=manager
                        )

                        # ポーリング機能のため、job_idをクライアント側に渡す
                        response = {
                            "job_id" : job.job_id,
                            "status" : "processing"
                        }

                        send_mmp_message(
                            connection=connection,
                            json_data=response,
                            media_type=None,
                            payload=None
                        )
except KeyboardInterrupt:
    print("\nサーバーを停止します。")