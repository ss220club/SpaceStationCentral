from app.core.db import init_db


def init() -> None:
    init_db()

if __name__ == "__main__":
    init()
