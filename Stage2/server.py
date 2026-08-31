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


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((SERVER_ADDRESS, SERVER_PORT))
    server_socket.listen(1)

    while True:
        connection, client_address = server_socket.accept()

        with connection:
            try:
                json_data, media_type, saved_path = recv_mmp_message(
                    connection=connection,
                    save_dir=SERVER_UPLOAD_DIR
                )
            except ValueError:
                print("不正なMMPデータです。")
                continue

            if json_data["operation"] == "check_status":
                job_id = json_data["job_id"]
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

            else:
                operation = json_data["operation"]
                params = json_data["params"]

                if media_type is not None and saved_path is not None:
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
                        output_path = create_output_path(
                            operation=operation,
                            media_type=media_type,
                            params=params
                        )

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
                        
