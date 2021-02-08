"""Runs TwitterTimeline flow to get twitter timelines of Scottish business websites.

TODO: A lot of the getter functions here need to be refactored into research_daps
"""
import json
import os
from collections import Counter
from datetime import datetime
from functools import lru_cache
from itertools import chain
from pathlib import Path
from typing import List, Dict, Set

import toolz.curried as t
from metaflow import S3, Run
from loguru import logger
from research_daps.flows.tweet_getter import twitter_timeline
from dotenv import find_dotenv, load_dotenv

from sg_covid_impact import config
from sg_covid_impact.utils.metaflow import update_model_config, execute_flow


class InvalidFlow(Exception):
    pass


def get_valid_regex_matches(run_id: int) -> Dict[str, Dict[str, int]]:
    """Fetch valid regex matches from `WebsiteRegex` flow for run `run_id`."""
    run = Run(f"WebsiteRegex/{run_id}")
    if run.successful:
        return filter_invalid(run.data.regex_matches_by_domain)
    else:
        raise InvalidFlow(f"websiteregex/{run_id} was not successful")


def is_valid(item: dict) -> bool:
    """Validates whether a regex match dict is valid."""
    k, v = item
    return (k is not None) and (not k.startswith("__BADPARSE__")) and (v != {})


def filter_invalid(d: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
    """Filters invalid regex matches."""
    return t.itemfilter(is_valid, d)


def joiner(regex_matches: List[Dict[str, Dict[str, int]]]) -> Dict[str, Dict[str, int]]:
    """Joins series of regex matches together.

    Example:

    ```python
    >> joiner(
         [{"foo.com": {"@foo": 2}},
          {"foo.com": {"@foo": 2, "@foo_marketing": 3}}]
          {"bar.com": {"@bar": 10}}
          )
    {"foo.com": {"@foo": 4, "@foo_marketing": 3}, "bar.com": {"@bar": 10}}
    ```
    """
    return t.merge_with(lambda x: t.merge_with(sum, x), regex_matches)


def does_handle_exist(handle: str) -> bool:
    """Checks whether `handle` has already been collected."""
    store = existing_handle_store()
    if handle in store:  # Fast check using cache
        return True
    else:  # Update store and test again
        logger.info("Updating handle store")
        existing_handle_store.cache_clear()
        store = existing_handle_store()
        return handle in store


@lru_cache
def existing_handle_store(s3_location: str) -> Set[str]:
    """Cached store of completed twitter handles."""
    s3_location = f"{s3_location}/.completed"
    with S3(s3root=s3_location) as s3:
        return set(map(lambda x: x.key, s3.list_paths()))


def auto_generate_blacklist(
    regex_matches: Dict[str, Dict[str, int]], threshold: int = 3
) -> List[str]:
    """Generate twitter handle blacklist based on frequency threshold."""
    c: Counter = Counter()
    for _, v in regex_matches.items():
        c.update(v.keys())
    return [k for k, v in c.items() if v > 3]


def tweet_id_to_timestamp(tweet_id: int) -> datetime:
    """Convert tweet id to timestamp."""
    offset = 1288834974657
    tstamp = (tweet_id >> 22) + offset
    return datetime.utcfromtimestamp(tstamp / 1000)


def timestamp_to_tweet_id(timestamp: datetime) -> int:
    """Convert timestamp to twitter id."""
    offset = 1288834974657
    return ((int(timestamp.strftime("%s")) * 1_000) - offset) << 22


def regex_matches_to_unique_handles(
    regex_matches: Dict[str, Dict[str, int]]
) -> List[str]:
    """Sorted list of unique twitter handles from `regex_matches`."""
    return t.pipe(
        regex_matches.values(),
        t.map(lambda x: x.keys()),
        chain.from_iterable,
        set,
        sorted,
        list,
    )


def existing_persistent_failures(s3_location: str) -> Set[str]:
    """Returns existing failures, that retrying will not solve."""
    s3_location = f"{s3_location}/.failures"
    with S3(s3root=s3_location) as s3:
        return set(map(lambda x: x.key, s3.list_paths()))


def get_handles(run_id: int) -> List[str]:
    """Twitter handles to fetch user timelines for."""
    regex_matches = get_valid_regex_matches(run_id)
    filter_list = set(auto_generate_blacklist(regex_matches, threshold=3))

    return t.pipe(
        regex_matches,
        regex_matches_to_unique_handles,
        t.filter(lambda x: x not in filter_list),
        list,
    )


def get_already_complete(s3_location: str) -> Set[str]:
    """Return already 'complete' collections."""
    fails = existing_persistent_failures(s3_location)
    existing_handles = existing_handle_store(s3_location)
    return fails | existing_handles


if __name__ == "__main__":
    load_dotenv(find_dotenv())  # API keys

    config_ = config["flows"]["twitter_timeline"]
    params = config_["params"]
    s3_location = params["s3_location"]

    # Derive twitter API parameter
    since_id = timestamp_to_tweet_id(datetime.strptime(params["since"], "%d/%m/%Y"))
    api_parameters = {"since_id": since_id, "include_rts": params["include_rts"]}

    # Generate handles from metaflow run containing handle data
    run_id = config["flows"]["handle_finder"]["run_id"]
    already_completed = get_already_complete(s3_location)
    handles = [
        handle for handle in get_handles(run_id) if handle not in already_completed
    ]

    logger.info(f"{len(handles)} twitter id's to collect. ")
    with open("handles.txt", "w") as f:
        f.write("\n".join(handles))

    cmd_params = {
        "--s3-location": str(s3_location),
        "--test_mode": str(params["test_mode"]),
        "--handle-file": str(Path(__file__).resolve().parents[0] / "handles.txt"),
        "--consumer-key": str(os.environ["consumer_key"]),
        "--consumer-secret": str(os.environ["consumer_secret"]),
        "--api-parameters": json.dumps(api_parameters),
    }
    flow_file = Path(twitter_timeline.__file__).resolve()
    run_id = execute_flow(
        flow_file,
        cmd_params,
        metaflow_args={
            "--package-suffixes": ".py,.txt",
            # "--metadata": "local",
            # "--datastore": "local",
            "--environment": "conda",
        },
    )

    config_["run_id"] = run_id
    update_model_config(["flows", "twitter_timeline"], config_)
