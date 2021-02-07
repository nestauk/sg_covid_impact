"""Downloads and filters raw tweets, splitting user store and tweet store."""
import json
import logging
import os
from subprocess import Popen, CalledProcessError
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Any, Tuple, List, Dict, Generator

from dotenv import find_dotenv, load_dotenv
import toolz.curried as t
import tqdm

from sg_covid_impact import project_dir
from sg_covid_impact.twitter.utils import timestamp_to_tweet_id

# Type aliases
UserHandle = str
UserInfo = Dict[str, Any]
Tweets = List[Dict[str, Any]]


def get_all(path: Path) -> Generator[List[Tweets], None, None]:
    """Generator yielding tweet data one account at a time."""

    keys = t.pipe(
        path.glob("[a-zA-Z0-9]*"),
        t.map(lambda p: p.rglob("*")),
        chain.from_iterable,
        t.filter(lambda x: x.is_file()),
        list,
    )

    logging.info(f"{len(keys)} twitter handles.")

    for organisation in keys:
        logging.info(organisation)
        with organisation.open() as f:
            yield json.load(f)


def process_org_tweets(tweets: List[Tweets]) -> Tuple[UserInfo, Tweets]:
    """Takes tweets of each org."""
    user = t.pipe(tweets, t.first, t.get("user"))

    @t.curry
    def drop_key_inplace(key: Any, d: dict) -> dict:
        d.pop(key)
        return d

    @t.curry
    def update_key_inplace(key: Any, value: Any, d: dict) -> dict:
        d[key] = value
        return d

    @t.curry
    def keep_keys(keys: List[Any], d: dict) -> dict:
        return {k: v for k, v in d.items() if k in keys}

    logging.info(f"{user['screen_name']}: {len(tweets)} tweets")

    tweet_id = timestamp_to_tweet_id(datetime(day=1, month=1, year=2019))
    columns = [
        "created_at",
        "id",
        "text",
        "user",
        "followers_count",
        "friends_count",
        "retweet_count",
        "favorite_count",
        "lang",
    ]

    return user, t.pipe(
        tweets,
        # Filter retweets
        t.filter(lambda tweet: t.get("retweeted_status", tweet, None) is None),
        # 2019 onwards only
        t.filter(lambda tweet: tweet["id"] > tweet_id),
        # Only keep columns we need, truncating user info
        t.map(keep_keys(columns)),
        t.map(update_key_inplace("user", user["screen_name"])),
        list,
    )


def download_tweets_from_s3(path: Path) -> None:
    """Download scraped tweets to `path` from S3 store."""
    cmd = " ".join(
        [
            "aws",
            "s3",
            "cp",
            "s3://nesta-glass/twitter/",
            str(path),
            "--recursive",
        ]
    )

    proc = Popen(
        cmd,
        shell=True,
    )
    while proc.poll():
        print(proc.communicate())
    proc.wait()
    return_value = proc.returncode

    if return_value != 0:
        raise CalledProcessError(return_value, cmd)


if __name__ == "__main__":
    load_dotenv(find_dotenv())

    in_path = (
        Path(os.environ.get("temp_dir") or f"{project_dir}/data/interim") / "twitter_s3"
    )

    out_path = (
        Path(os.environ.get("temp_dir") or f"{project_dir}/data/interim") / "twitter"
    )
    out_path.mkdir(exist_ok=True)

    # Download S3 tweet data
    download_tweets_from_s3(in_path)

    # Process tweet data
    tweets: List[Tuple[UserInfo, Tweets]] = t.pipe(
        get_all(in_path),
        t.curry(tqdm.tqdm, desc="Downloaded"),
        t.filter(lambda x: x != []),
        t.map(process_org_tweets),
        t.filter(lambda x: x[1] != []),
        list,
    )

    # Export tweets
    with (out_path / "tweets.json").open("w") as f:
        json.dump([user_tweets for _, user_tweets in tweets], f)

    # Export users
    with (out_path / "users.json").open("w") as f:
        json.dump([user for user, _ in tweets], f)
