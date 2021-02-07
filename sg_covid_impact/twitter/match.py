"""Match tweets to organisations."""
from collections import Counter
from typing import Any, Tuple, List, Set, Dict, Optional, KeysView

import toolz.curried as t
import tqdm
from fuzzywuzzy import process, fuzz

# Type aliases
UserHandle = str
UserInfo = Dict[str, Any]
Tweets = List[Dict[str, Any]]


def user_website_lookup(users: List[UserInfo]) -> Dict[UserHandle, str]:
    """Build lookup from twitter screen name to URL in profile."""
    return t.pipe(
        users,
        t.map(
            lambda user: (
                user["screen_name"],
                t.get_in(["entities", "url", "urls", 0, "display_url"], user),
            )
        ),
        t.curry(tqdm.tqdm, desc="Processed"),
        dict,
        t.valfilter(lambda v: v is not None),
    )


def build_blacklist(matches: Dict[str, Dict[UserHandle, int]]) -> Set[UserHandle]:
    return t.pipe(
        matches.values(),
        t.merge_with(len),
        Counter,
        lambda c: c.most_common(),
        t.filter(lambda x: x[1] > 5),
        t.map(t.first),
        set,
    )


def extract_twitter_id(
    item: Tuple[str, Dict[UserHandle, int]], lookup: Dict[UserHandle, str]
) -> Tuple[str, Optional[UserHandle]]:
    """Extract twitter screen-name for website from list of potentials"""
    website, match = item
    n_keys = len(match.keys())

    if n_keys == 0:
        return (website, None)
    elif n_keys == 1:  # Take what we can get
        return (website, match.popitem()[0])
    else:
        similarities = process.extract(website, match.keys())
        threshold = 70
        if similarities[0][1] >= threshold:
            return (website, similarities[0][0])
        else:  # Check website for user
            potentials = website_in_account(website, match.keys(), lookup, threshold)
            return (website, potentials[1])


def website_in_account(
    website: str,
    keys: KeysView[UserHandle],
    lookup: Dict[UserHandle, str],
    threshold: int,
) -> Tuple[str, Optional[str]]:
    """Return twitter screen name in `lookup` that best matches `website`."""
    result = t.pipe(
        keys,
        t.map(lambda x: (x, lookup.get(x))),  # Get websites of candidates (if existing)
        t.filter(lambda x: x[1] is not None),
        # Similarities of websites
        t.map(lambda x: (x[0], fuzz.ratio(website, x[1]))),
        t.filter(lambda name_score: name_score[1] >= threshold),
        # Sort and get best
        t.curry(sorted, key=lambda x: x[1]),
        t.map(t.first),  # Name not score
        list,
        t.get(0, default=None),
    )
    return (website, result)


def filter_accounts(
    item: Tuple[str, Dict[str, int]], blacklist: Set[str]
) -> Tuple[str, Dict[str, int]]:
    """Remove blacklisted accounts."""
    website, match = item
    return (website, t.keyfilter(lambda k: k not in blacklist, match))
