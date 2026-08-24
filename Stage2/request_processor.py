import uuid

from pathlib import Path
from typing import Any


from job_manager import(
    Job,
    JobManager
)


from ffmpeg_service import(
    compress_video,
    resize_video,
    change_aspect_ratio,
    extract_audio,
    create_clip
)


OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def create_output_path(
        operation: str,
        media_type: str,
        params: dict[str, Any]
) -> Path:

    if operation in {"compress", "resize", "change_aspect_ratio"}:
        suffix = media_type

    elif operation == "extract_audio":
        suffix = "mp3"

    elif operation == "create_clip":
        suffix = params["output_format"].lower()

        if suffix not in {"gif", "webm"}:
            raise ValueError("出力形式はgifまたはwebmを指定してください。")

    else:
        raise ValueError("不正なoperationです。")

    output_path = OUTPUT_DIR / f"{uuid.uuid4()}.{suffix}"

    return output_path


def process_job(
        job: Job,
        job_manager: JobManager
) -> None:

    operation = job.operation

    try:
        if operation == "compress":
            compress_video(
                input_path=job.input_path,
                output_path=job.output_path
            )

        elif operation == "resize":
            resize_video(
                input_path=job.input_path,
                output_path=job.output_path,
                width=job.params["width"],
                height=job.params["height"]
            )

        elif operation == "change_aspect_ratio":
            change_aspect_ratio(
                input_path=job.input_path,
                output_path=job.output_path,
                aspect_width=job.params["aspect_width"],
                aspect_height=job.params["aspect_height"]
            )

        elif operation == "extract_audio":
            extract_audio(
                input_path=job.input_path,
                output_path=job.output_path
            )

        elif operation == "create_clip":
            create_clip(
                input_path=job.input_path,
                output_path=job.output_path,
                start_time=job.params["start_time"],
                end_time=job.params["end_time"],
                output_format=job.params["output_format"]
            )

        else:
            raise ValueError("不正なoperationです。")

        job_manager.update_status(
            job_id=job.job_id,
            status="completed"
        )

        print("動画処理が完了しました。")

    except Exception as error:
        job_manager.fail_job(
            job_id=job.job_id,
            error=str(error)
        )

        print("動画処理に失敗しました。")