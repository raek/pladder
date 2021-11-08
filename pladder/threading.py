from contextlib import contextmanager
import logging
from threading import Thread


logger = logging.getLogger("pladder.threading")


@contextmanager
def background_thread(name, work_fn, stop_fn, sync_fn=lambda: True):
    t = Thread(target=work_fn)
    try:
        logger.debug(f"Starting {name} thread")
        t.start()
        if not sync_fn():
            raise Exception(f"{name} thread work function did not start")
        logger.info(f"{name} thread started")
        yield
    finally:
        logger.debug(f"Stopping {name} thread")
        stop_fn()
        t.join()
        logger.info(f"{name} thread stopped")
