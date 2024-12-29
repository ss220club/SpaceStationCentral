from datetime import datetime, timedelta

from pydantic import BaseModel, Field, field_serializer, field_validator


class NewWhitelist(BaseModel):
    player_id: str
    type: str
    admin_id: str
    issue_time: datetime | None = Field(default_factory=datetime.now)
    duration: timedelta | None = timedelta(days=30)
    valid: bool | None = True

    @field_validator("issue_time")
    @classmethod
    def parse_issue_time(cls, issue_time: str | datetime) -> datetime:
        """Validate and parse `issue_time` into a datetime object."""
        if isinstance(issue_time, datetime):
            return issue_time
        return datetime.fromisoformat(issue_time)

    @field_serializer("issue_time", when_used="json")
    @classmethod
    def serialize_issue_time(cls, issue_time: datetime) -> str:

        return issue_time.isoformat()

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, duration: float | timedelta) -> timedelta:
        """Ensure duration is non-negative."""
        if isinstance(duration, timedelta):
            return duration
        if duration < 0:
            raise ValueError("Duration must be a non-negative integer.")
        return timedelta(seconds=duration)

    @field_serializer("duration", when_used="json")
    @classmethod
    def serialize_duration(cls, duration_secs: timedelta) -> float:
        return duration_secs.total_seconds()
