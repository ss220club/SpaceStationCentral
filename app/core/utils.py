from datetime import UTC, datetime


# TODO: Make an appocalypse happen, so theres no more timezone issues
def utcnow2() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
