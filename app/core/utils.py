import datetime


# TODO: Make an appocalypse happen, so theres no more timezone issues
def utcnow2() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
