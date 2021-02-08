"""Module to construct a regex that find twitter handles and twitter.com URL's."""
TWITTER_HANDLE_FORMAT = r"[a-zA-Z0-9_]{1,15}"


def twitter_handle_regex() -> str:
    """Regex to find twitter handles."""

    pre = r"\B"
    post = r"[\s.,<]"  # Allow whitespace and some punctuation after handle
    # 1. Hard word boundary (incl. HTML closing tag)
    # 2. Capture `handle_format`
    # 3. Either: `post` or $
    return r"{}@({}){}|{}@({})$".format(
        pre, TWITTER_HANDLE_FORMAT, post, pre, TWITTER_HANDLE_FORMAT
    )


def twitter_link_regex() -> str:
    """Regex to find links to 'twitter.com'."""
    return r"twitter.com/({})".format(TWITTER_HANDLE_FORMAT)


TWITTER_REGEX = r"{}|{}".format(twitter_handle_regex(), twitter_link_regex())
