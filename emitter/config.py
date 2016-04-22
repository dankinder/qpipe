import os

class Backend:
    THREADING = "threading"
    MULTIPROCESSING = "multiprocessing"
    DUMMY = "dummy"

_backend = None

def get_backend():
    global _backend
    return _backend

def is_backend(value):
    global _backend
    return _backend == value

def set_backend(value):
    global _backend
    _backend = value

def _initialize():
    global _backend
    if _backend:
        return

    _backend = os.getenv("EMITTER_BACKEND", Backend.MULTIPROCESSING)

    if not _backend in [Backend.THREADING, Backend.MULTIPROCESSING, Backend.DUMMY]:
        raise RuntimeError("Emitter backend is not valid: " + str(_backend))

_initialize()

