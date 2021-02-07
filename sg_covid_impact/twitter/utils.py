"""Twitter utilities."""
from datetime import datetime

OFFSET = 1288834974657


def tweet_id_to_timestamp(tweet_id: int) -> datetime:
    """Convert tweet id to timestamp."""
    tstamp = (tweet_id >> 22) + OFFSET
    return datetime.utcfromtimestamp(tstamp / 1000)


def timestamp_to_tweet_id(timestamp: datetime) -> int:
    """Convert timestamp to twitter id."""
    return ((int(timestamp.strftime("%s")) * 1_000) - OFFSET) << 22
