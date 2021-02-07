"""NLP utils & functions for Glass description processing and salient term extraction."""
from itertools import combinations, chain
from typing import Any, Dict, Iterable, List, Optional
import re
import string

import nltk
import pandas as pd
import toolz.curried as t
from gensim import models
from Levenshtein import distance
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer


from sg_covid_impact.utils.list_utils import flatten_freq

nltk.download("stopwords", quiet=True)
nltk.download("punkt", quiet=True)

_STOP_WORDS = set(
    stopwords.words("english") + list(string.punctuation) + ["\\n"] + ["quot"]
)

# WHAT IS _REGEX_STR?
# Each failed match means it falls through to the next to catch
# 0: URL's
# 1: ???
# 2: ???
# 3: ???
# 4: Twitter id like
# 5: Enclosed in angle brackets
# 6: Apostrophe
# 7: Words (including underscores)
# 8: Single non-whitespace character
_REGEX_STR = [
    r"http[s]?://(?:[a-z]|[0-9]|[$-_@.&+]|" r"[!*\(\),](?:%[0-9a-f][0-9a-f]))+",
    r"(?:\w+-\w+){2}",  # TODO: is this useful?
    r"(?:\w+-\w+)",  # TODO: is this useful?
    r"(?:\\\+n+)",  # TODO: is this useful?
    r"(?:@[\w_]+)",
    r"<[^>]+>",
    r"(?:\w+'\w)",
    r"(?:[\w_]+)",
    r"(?:\S)",  # TODO: is this useful?
    r"(?:\S)",
]

# Create the tokenizer which will be case insensitive and will ignore space.
tokens_re = re.compile(r"(" + "|".join(_REGEX_STR) + ")", re.VERBOSE | re.IGNORECASE)


def tokenize_document(text, remove_stops=False):
    """Preprocess a whole raw document.
    Args:
        text (str): Raw string of text.
        remove_stops (bool): Flag to remove english stopwords
    Return:
        List of preprocessed and tokenized documents
    """
    return [
        clean_and_tokenize(sentence, remove_stops)
        for sentence in nltk.sent_tokenize(text)
    ]


def clean_and_tokenize(text, remove_stops):
    """Preprocess a raw string/sentence of text.
    Args:
       text (str): Raw string of text.
       remove_stops (bool): Flag to remove english stopwords

    Return:
       tokens (list, str): Preprocessed tokens.
    """
    tokens = tokens_re.findall(text)
    _tokens = [t.lower() for t in tokens]
    filtered_tokens = [
        token.replace("-", "_")
        for token in _tokens
        # Conditions to be kept:
        # - Longer than 2 characters if `remove_stops`
        # - Not be a stop words if `remove_stops`
        # - No digits in token
        # - At least one ascii lowercase character
        if not (remove_stops and len(token) <= 2)
        and (not remove_stops or token not in _STOP_WORDS)
        and not any(x in token for x in string.digits)
        and any(x in token for x in string.ascii_lowercase)
    ]
    return filtered_tokens


def tokenize(text: str, tokens_re: re.Pattern) -> Iterable[str]:
    """Preprocess a raw string/sentence of text. """
    return t.pipe(
        text,
        tokens_re.findall,
        lambda tokens: chain.from_iterable(tokens) if tokens_re.groups > 1 else tokens,
        t.filter(None),
    )


def make_ngram(tokenised_corpus, n_gram=2, threshold=10):
    """Extract bigrams from tokenised corpus
    Args:
        tokenised_corpus (list): List of tokenised corpus
        n_gram (int): maximum length of n-grams. Defaults to 2 (bigrams)
        threshold (int): min number of n-gram occurrences before inclusion
    Returns:
        ngrammed_corpus (list)
    """
    tokenised = tokenised_corpus.copy()
    t = 1
    # Loops while the ngram length less / equal than our target
    while t < n_gram:
        phrases = models.Phrases(tokenised, threshold=threshold)
        bigram = models.phrases.Phraser(phrases)
        tokenised = bigram[tokenised]
        t += 1
    return list(tokenised)


def make_ngrams_v2(
    documents: List[List[str]], n: int = 2, phrase_kws: Optional[Dict[str, Any]] = None
) -> List[List[str]]:
    """Create ngrams using Gensim's phrases.

    Args:
        documents: Tokenized documents.
        n: The `n` in n-gram.
        phrase_kws: Passed to `gensim.models.Phrases`.

    Return:
        N-grams

    #UTILS
    """
    assert isinstance(n, int)
    if n < 2:
        raise ValueError("Pass n >= 2 to generate n-grams")

    def_phrase_kws = {
        "scoring": "npmi",
        "threshold": 0.25,
        "min_count": 2,
        "delimiter": b"_",
    }
    if phrase_kws is None:
        phrase_kws = def_phrase_kws
    else:
        def_phrase_kws.update(phrase_kws)
        phrase_kws = def_phrase_kws

    t = 1
    while t < n:
        phrases = models.Phrases(documents, **phrase_kws)
        bigram = models.phrases.Phraser(phrases)
        del phrases
        tokenised = bigram[documents]
        t += 1

    return list(tokenised)


def salient_words_per_category(token_df, corpus_freqs, thres, top_words=100):
    """Create a list of salient terms in a sub-corpus (normalised by corpus
    frequency).
    Args:
        tokens (list or series): List where every element is a tokenised doc
        corpus_freqs (df): frequencies of terms in the whole corpus
        thres (int): number of occurrences of a term in the subcorpus
        top_words (int): number of salient words to output

    #Returns:
        A df where every element is a term with its salience
    """
    # Create subcorpus frequencies
    subcorpus_freqs = flatten_freq(token_df)
    # Merge with corpus freqs
    merged = pd.concat([pd.DataFrame(subcorpus_freqs), corpus_freqs], axis=1, sort=True)
    # Normalise
    merged["salience"] = merged.iloc[:, 0] / merged.iloc[:, 1]
    # Filter
    results = (
        merged.loc[merged.iloc[:, 0] > thres]
        .sort_values("salience", ascending=False)
        .iloc[:top_words]
    )
    results.columns = ["sub_corpus", "corpus", "salience"]
    return results


def get_category_salience(
    df, sel_var, sel_term, text_var, corpus_freqs, thres=5, top_words=100
):
    """Returns a list of salient terms per category in a corpus
    Args:
        df (df): df with
        sel_var (str): grouping variable
        sel_term (str): grouping term
        text_var (str): variable with tokenised document
        corpus_freqs (df): term frequencies in the corpus
        thres (float): min number of word occurrences
        top_words (int): number of words to report
    Returns:
        Salient terms in a category
    """
    # Subset by the categoru
    rel_corp = df.loc[df[sel_var] == sel_term][text_var]
    # Return salient terms
    salient_rel = salient_words_per_category(
        list(rel_corp), corpus_freqs, thres, top_words
    )
    # Rename df
    salient_renamed = salient_rel.rename(
        columns={
            "sub_corpus": f"{str(sel_term)}_freq",
            "corpus": "all_freq",
            "salience": f"{str(sel_term)}_salience",
        }
    )
    return salient_renamed


def remove_dupes(results, div, lev_length=10, lev_dist=3):
    """Removes duplicates from list of salient terms
    Args:
        lev_length: Minimum length to consider for levenshtein comparisons
        lev_dist: Levenshtein distance threshold for long ngrams

    """
    ps = PorterStemmer()

    # Pairs of terms in the index
    pairs = list(combinations(results.index, 2))

    # Find pairs with the same stem
    close_pairs = []
    for p in pairs:

        if ps.stem(p[0]) == ps.stem(p[1]):
            close_pairs.append(list(p))
        # Stemming will not work with eg bigrams.
        # For longer ngrams we consider levenshtein distances
        else:
            if len(p[0]) > lev_length:
                if distance(p[0], p[1]) <= lev_dist:
                    close_pairs.append(list(p))

    # Drop the least salient term
    drop = []

    for c in close_pairs:
        comp = results.loc[c]
        drop_ = comp[f"{div}_freq"].idxmin()
        drop.append(drop_)

    rev_list = results.loc[~results.index.isin(drop)]

    return rev_list
