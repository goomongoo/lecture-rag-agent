# server/core/state.py

from threading import Lock
from collections import defaultdict


_processing_status = defaultdict(int)
_status_lock = Lock()
_faiss_locks = defaultdict(Lock)


def mark_processing(user: str, course: str):
    with _status_lock:
        _processing_status[(user, course)] += 1


def mark_done(user: str, course: str):
    with _status_lock:
        key = (user, course)
        if key in _processing_status:
            _processing_status[key] = max(_processing_status[key] - 1, 0)


def get_status(user: str, course: str) -> int:
    with _status_lock:
        return _processing_status.get((user, course), 0)
    

def with_faiss_lock(user: str, course: str):
    return _faiss_locks[(user, course)]
