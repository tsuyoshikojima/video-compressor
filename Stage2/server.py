import socket

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

            operation = json_data["operation"]
            params = json_data["params"]

            if media_type is not None and saved_path is not None:
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

                process_job(
                    job=job,
                    job_manager=manager
                )

                if job.status == "completed":
                    json_data = {
                        "job_id" : job.job_id,
                        "status" : "completed"
                    }

                    send_mmp_message(
                        connection=connection,
                        json_data=json_data,
                        media_type=job.output_path.suffix.removeprefix("."),
                        payload=job.output_path
                    )

                elif job.status == "failed":
                    json_data = {
                        "job_id" : job.job_id,
                        "status" : "failed",
                        "error_code" : "PROCESSING_FAILED",
                        "description" : job.error,
                        "solution" : "入力ファイルとパラメータを確認してください。"
                    }

                    send_mmp_message(
                        connection=connection,
                        json_data=json_data,
                        media_type=None,
                        payload=None
                    )

                