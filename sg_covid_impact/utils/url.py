"""Utilities for working with URL's."""
from urllib3.util.url import parse_url as parse_url_


def parse_url(url: str):
    """Safer parse url by stripping weird characters first."""
    return parse_url_(url.strip("‘'\""))
