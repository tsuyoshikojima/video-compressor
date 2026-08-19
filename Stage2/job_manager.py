import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Job:
    job_id: str
    client_ip: str
    operation: str
    status: str
    input_path: Path
    output_path: Path
    params: dict[str, Any]
    error: str| None = None


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create_job(
            self,
            client_ip: str,
            operation: str,
            input_path: Path,
            output_path: Path,
            params: dict[str, Any]
    ) -> Job:

        job_id = str(uuid.uuid4())

        job = Job(
            job_id=job_id,
            client_ip=client_ip,
            operation=operation,
            status="processing",
            input_path=input_path,
            output_path=output_path,
            params=params,
        )

        self._jobs[job_id] = job

        return job

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def update_status(
            self,
            job_id: str,
            status: str
    ) -> None:

        job = self.get_job(job_id)

        if job is None:
            raise ValueError("指定されたJobが存在しません。")

        job.status = status

    def fail_job(
            self, 
            job_id: str,
            error: str
    ) -> None:

        job = self.get_job(job_id)

        if job is None:
            raise ValueError("指定されたJobが存在しません。")

        job.status = "failed"
        job.error = error

    def remove_job(self, job_id: str) -> None:

        job = self.get_job(job_id)

        if job is None:
            raise ValueError("指定されたJobが存在しません。")

        del self._jobs[job_id]

    def has_active_job(self, client_ip: str) -> bool:

        for job in self._jobs.values():
            if job.client_ip == client_ip and job.status == "processing":
                return True

        return False

manager = JobManager()

job = manager.create_job(
    client_ip="127.0.0.1",
    operation="compress",
    input_path=Path("input.mp4"),
    output_path=Path("output.mp4"),
    params={}
)
