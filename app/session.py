import os
import time

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

SESSION_FILE = os.path.join(
    BASE_DIR,
    "..",
    "session.json"
)

SESSION_TIME_FILE = os.path.join(
    BASE_DIR,
    "..",
    "session_time.txt"
)

SESSION_EXPIRATION = 600


def is_session_valid():

    if not os.path.exists(
        SESSION_FILE
    ):
        return False

    if not os.path.exists(
        SESSION_TIME_FILE
    ):
        return False

    try:

        with open(
            SESSION_TIME_FILE,
            "r"
        ) as f:

            ts = float(
                f.read().strip()
            )

        return (
            time.time() - ts
        ) < SESSION_EXPIRATION

    except:
        return False


async def save_session(context):

    await context.storage_state(
        path=SESSION_FILE
    )

    with open(
        SESSION_TIME_FILE,
        "w"
    ) as f:

        f.write(
            str(time.time())
        )