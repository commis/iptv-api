import threading
import time
from uuid import uuid4

from core.singleton import singleton


@singleton
class TaskManager:
    def __init__(self):
        self._tasks = {}
        self._lock = threading.RLock()

    def create_task(self, **kwargs):
        task_id = str(uuid4()).replace('-', '')
        task = {
            "id": task_id,
            "type": kwargs['type'],
            "description": kwargs['description'],
            'url': kwargs['url'],
            "status": "initializing",
            "total": kwargs['total'],
            "progress": 0,
            "processed": 0,
            "success": 0,
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
            "result": None,
            "error": None
        }

        with self._lock:
            self._tasks[task_id] = task
            task["status"] = "pending"

        return task_id

    def clear(self):
        with self._lock:
            self._tasks.clear()

    def get_tasks(self):
        with self._lock:
            return [{"id": task["id"], "status": task["status"]} for task in self._tasks.values()]

    def get_task(self, task_id):
        with self._lock:
            return self._tasks.get(task_id)

    def update_task(self, task_id, **kwargs):
        with self._lock:
            if task_id not in self._tasks:
                return False

            if 'status' in kwargs and kwargs['status'] not in {'pending', 'running', 'completed', 'failed'}:
                return False

            task = self._tasks[task_id]
            task.update(kwargs)
            task["updated_at"] = int(time.time())
            return True

    def delete_task(self, task_id):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task["status"] not in {"pending", "completed", "failed"}:
                return False

            return self._tasks.pop(task_id, None) is not None

    def safe_get_and_update_task(self, task_id, update_func):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            update_func(task)
            task["updated_at"] = int(time.time())
            return True


task_manager = TaskManager()
