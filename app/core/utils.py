import datetime


def utcnow2() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
