import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

class QueueManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QueueManager, cls).__new__(cls)
            cls._instance.jobs = {}
        return cls._instance

    def create_job(self, type: str, payload: Dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "id": job_id,
            "type": type,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "payload": payload,
            "result": None,
            "error": None,
            "progress": 0
        }
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> Dict[str, Dict]:
        return self.jobs

    def update_job(self, job_id: str, status: str = None, result: Any = None, error: str = None, progress: int = None):
        if job_id in self.jobs:
            if status:
                self.jobs[job_id]["status"] = status
            if result:
                self.jobs[job_id]["result"] = result
            if error:
                self.jobs[job_id]["error"] = error
            if progress is not None:
                self.jobs[job_id]["progress"] = progress
            self.jobs[job_id]["updated_at"] = datetime.now().isoformat()
