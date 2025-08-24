import os
import time
import uuid


def current_timestamp() -> int:
    return int(time.time())


_VAULT_ID = None


def get_vault_id() -> str:
    global _VAULT_ID
    if _VAULT_ID is None:
        if not os.path.isfile("data/VAULT_ID"):
            with open("data/VAULT_ID", "w") as f:
                f.write(str(uuid.uuid4()))
        _VAULT_ID = open("data/VAULT_ID").read().strip()
    return _VAULT_ID