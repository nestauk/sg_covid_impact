"""Test twitter handle and link finder."""
import pytest
import re

from twitter_regex import TWITTER_REGEX


@pytest.fixture
def twitter_text_sample():
    return """twitter.com/url_handle some text @repeat @bar
    @dont_allow@adjoining twitter@handles no dangling @ @'s
    no @reallylongtwittername but @underscores_ ok @no-dashes
    @repeat text @us_fullstop.
    <a href="https://twitter.com/handle_in_link">@in_html</a>
     @endoffile"""


def test_twitter_regex_matches(twitter_text_sample):
    regex = re.compile(TWITTER_REGEX)
    handles = regex.findall(twitter_text_sample)

    expected_matches = [
        # Column 1: Handle
        # Column 2: Handle at end of line
        # Column 3: Twitter URL
        ("", "", "url_handle"),
        ("repeat", "", ""),
        ("bar", "", ""),
        ("underscores_", "", ""),
        ("repeat", "", ""),
        ("us_fullstop", "", ""),
        ("", "", "handle_in_link"),
        ("in_html", "", ""),
        ("", "endoffile", ""),
    ]
    assert handles == expected_matches

    text = "no twitter handles here"
    assert regex.findall(text) == []
