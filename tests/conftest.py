import time
import uuid


def new_virtual_channel(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def wait_until(predicate, timeout=1.5, poll=0.02):
    start = time.time()
    while time.time() - start <= timeout:
        if predicate():
            return True
        time.sleep(poll)
    return False


def hex_payloads(frames):
    return [bytes(f.data).hex() for f in frames]
