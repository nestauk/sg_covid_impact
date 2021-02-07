"""Getters for twitter data."""
import json
import os
from itertools import chain
from pathlib import Path
from typing import Any, List, Dict

from dotenv import find_dotenv, load_dotenv
import pandas as pd
import metaflow as mf
import toolz.curried as t

from sg_covid_impact.getters.glass import get_organisation
from sg_covid_impact import config
from sg_covid_impact import project_dir
from sg_covid_impact.twitter.match import (
    filter_accounts,
    extract_twitter_id,
    build_blacklist,
    user_website_lookup,
)
from sg_covid_impact.utils.metaflow import cache_getter_fn
from sg_covid_impact.utils.url import parse_url

# Type aliases
UserHandle = str
UserInfo = Dict[str, Any]
Tweets = List[Dict[str, Any]]

load_dotenv(find_dotenv())

RUN_ID: int = config["flows"]["webex"]["run_id"]


def get_users() -> List[UserInfo]:
    """Load twitter user data."""
    path = (
        Path(os.environ.get("temp_dir") or f"{project_dir}/data/interim")
        / "twitter"
        / "users.json"
    )
    with path.open() as f:
        return json.load(f)


def get_tweets() -> List[Tweets]:
    """Load twitter tweet data."""
    path = (
        Path(os.environ.get("temp_dir") or f"{project_dir}/data/interim")
        / "twitter"
        / "tweets.json"
    )
    with path.open() as f:
        return json.load(f)


@cache_getter_fn
def get_matches(run_id: int = RUN_ID) -> Dict[str, UserHandle]:
    """Lookup between glass URL and Twitter handle."""
    run = mf.Run(f"WebsiteRegex/{run_id}")

    matches = t.pipe(
        run.data.regex_matches_by_domain,
        t.keyfilter(lambda k: k is not None and "__BADPARSE__" not in k),
        t.valfilter(lambda v: v != {}),
    )

    # Build blacklist of frequent terms that we want to filter out
    blacklist = build_blacklist(matches)

    lookup = user_website_lookup(get_users())

    return t.pipe(
        matches.items(),
        t.map(lambda match: filter_accounts(match, blacklist)),
        t.map(lambda match: extract_twitter_id(match, lookup)),
        dict,
        t.valfilter(lambda v: v is not None),
    )


@cache_getter_fn
def get_glass_twitter_accounts() -> pd.DataFrame:
    """Tweets corresponding to Glass companies."""
    return (
        get_organisation()[["org_id", "website"]]
        .assign(website=lambda x: x.website.apply(lambda x: parse_url(x).netloc))
        .drop_duplicates()
        .merge(
            pd.Series(get_matches(), name="user"),
            left_on="website",
            right_index=True,
        )
        .assign(user=lambda x: x.user.str.lower())
    )


@cache_getter_fn
def get_glass_tweets() -> pd.DataFrame:
    glass_twitter_accounts = get_glass_twitter_accounts().drop("website", axis=1)

    glass_twitter_account_set = glass_twitter_accounts.user.pipe(set)
    tweets = t.pipe(
        get_tweets(),
        t.filter(lambda x: x[0]["user"].lower() in glass_twitter_account_set),
        chain.from_iterable,
        pd.DataFrame,
    ).assign(user=lambda x: x.user.str.lower())

    # TODO: what is the matching loss here? WHy does it exist?
    return glass_twitter_accounts.merge(tweets, on="user", how="inner").assign(
        created_at=lambda x: x.created_at.pipe(pd.to_datetime)
    )


@cache_getter_fn
def get_glass_twitter_user_info() -> pd.DataFrame:
    glass_twitter_accounts = (
        get_glass_twitter_accounts()
        .drop("website", axis=1)
        .rename(columns={"user": "screen_name"})
    )

    glass_twitter_account_set = glass_twitter_accounts.screen_name.pipe(set)
    users = t.pipe(
        get_users(),
        t.filter(lambda x: x["screen_name"].lower() in glass_twitter_account_set),
        pd.DataFrame,
    ).assign(screen_name=lambda x: x.screen_name.str.lower())

    # TODO: what is the matching loss here? WHy does it exist?
    return glass_twitter_accounts.merge(users, on="screen_name", how="inner").assign(
        created_at=lambda x: x.created_at.pipe(pd.to_datetime)
    )
