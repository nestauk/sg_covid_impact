# %%
"""Tokenises and ngrams Covid notices."""
import re
import string
from itertools import product
from typing import Any, Dict, Iterable, List, Optional

import toolz.curried as t
import nltk
from gensim.corpora import Dictionary
from metaflow import FlowSpec, step, Parameter
from nltk.stem import WordNetLemmatizer

from sg_covid_impact.getters.glass import get_notice
from sg_covid_impact.nlp import (
    make_ngrams_v2,
    tokenize,
    _STOP_WORDS,
)

N_TEST_DOCS = 1_000
SECOND_ORDER_STOP_WORDS = t.pipe(
    _STOP_WORDS,
    lambda stops: product(stops, stops),
    t.map(lambda x: f"{x[0]}_{x[1]}"),
    set,
    lambda stops: stops | _STOP_WORDS,
)
REGEX_TOKEN_TYPES = {
    "URL": r"(http[s]?://(?:[a-z]|[0-9]|[$-_@.&+]|[!*\(\),](?:%[0-9a-f][0-9a-f]))+)",
    "@word": r"(@[\w_]+)",
    "XML": r"(<[^>]+>)",
    "strip_apostrophe": r"(\w+)'\w",
    "word": r"([\w_]+)",
    "non-whitespace-char": r"(?:\S)",  # TODO: is this useful?
    "hyphenated": r"(\w+-[\w\d]+)",
}


def pre_token_filter(tokens: Iterable[str]) -> Iterable[str]:
    """Pre n-gram token filter."""

    filter_re = "|".join(
        [REGEX_TOKEN_TYPES["URL"], REGEX_TOKEN_TYPES["@word"], REGEX_TOKEN_TYPES["XML"]]
    )

    def predicate(token: str) -> bool:
        return (
            # At least one ascii letter
            any(x in token for x in string.ascii_lowercase)
            # No URL's | twitter ID's
            and not re.match(filter_re, token)
        )

    return filter(predicate, tokens)


def post_token_filter(tokens: Iterable[str]) -> Iterable[str]:
    """Post n-gram token filter."""

    def predicate(token: str) -> bool:
        return (
            # No short words
            (not len(token) <= 2)
            # No stopwords
            and (token not in SECOND_ORDER_STOP_WORDS)
        )

    return filter(predicate, tokens)


def token_converter(tokens: Iterable[str]) -> Iterable[str]:
    """Convert tokens."""

    def convert(token: str) -> str:
        return token.lower().replace("-", "_")

    return map(convert, tokens)


@t.curry
def filter_frequency(
    documents: List[str], kwargs: Optional[Dict[str, Any]] = None
) -> Iterable[str]:
    """Filter `documents` based on token frequency corpus."""
    dct = Dictionary(documents)

    default_kwargs = dict(no_below=10, no_above=0.9, keep_n=1_000_000)
    if kwargs is None:
        kwargs = default_kwargs
    else:
        kwargs = t.merge(default_kwargs, kwargs)

    dct.filter_extremes(**kwargs)
    return t.pipe(
        documents,
        t.map(lambda document: [token for token in document if token in dct.token2id]),
    )


class NoticeTokeniseFlow(FlowSpec):
    n_gram = Parameter(
        "n-gram",
        help="The `N` in N-gram",
        type=int,
        default=2,
    )
    test_mode = Parameter(
        "test_mode",
        help="Whether to run in test mode (fetch a subset of data)",
        type=bool,
        default=True,
    )

    @step
    def start(self):
        notices = get_notice().head(N_TEST_DOCS if self.test_mode else None)[
            ["notice_id", "snippet"]
        ]

        nltk.download("wordnet")
        lemmatiser = WordNetLemmatizer()

        tokens_re = re.compile(
            "|".join(
                [
                    REGEX_TOKEN_TYPES["URL"],
                    REGEX_TOKEN_TYPES["@word"],
                    REGEX_TOKEN_TYPES["XML"],
                    REGEX_TOKEN_TYPES["strip_apostrophe"],
                    REGEX_TOKEN_TYPES["hyphenated"],
                    REGEX_TOKEN_TYPES["word"],
                ]
            ),
            re.VERBOSE | re.IGNORECASE,
        )

        tokenize_ = t.curry(tokenize, tokens_re=tokens_re)

        notice_tokens = t.pipe(
            notices.snippet.values,
            # Tokenise and filter
            t.map(t.compose(list, pre_token_filter, token_converter, tokenize_)),
            list,
            # Filter low frequency terms (want to keep high frequency terms)
            filter_frequency(kwargs={"no_above": 1}),
            list,
            # N-gram
            t.curry(make_ngrams_v2, n=self.n_gram),
            # Lemmatise
            t.map(lambda document: [lemmatiser.lemmatize(word) for word in document]),
            # Filter ngrams: combination of stopwords, e.g. `of_the`
            t.map(t.compose(list, post_token_filter)),
            list,
            # Filter ngrams:  low (and very high) frequency terms
            filter_frequency,
            list,
        )

        notice_keys = notices.notice_id.values
        del notices

        self.docs = dict(zip(notice_keys, notice_tokens))
        self.next(self.end)

    @step
    def end(self):
        pass


if __name__ == "__main__":
    NoticeTokeniseFlow()


# %%

# unique_words = set(chain.from_iterable(notice_tokens))
# n_unique_words = len(unique_words)
# print(n_unique_words)
# # %%

# texts = notices.snippet.loc[lambda x: x.str.contains("-")].head().values.tolist()
# t.pipe(texts, t.first, tokenize_, list)
