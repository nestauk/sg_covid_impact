"""Extract salient terms in Glass descriptions by sector
"""
import logging
import pickle
import re
import pandas as pd
from toolz.curried import pipe

from sg_covid_impact.make_sic_division import extract_sic_code_description
from sg_covid_impact.sic import load_sic_taxonomy
from sg_covid_impact.nlp import (
    clean_and_tokenize,
    make_ngram,
    flatten_freq,
    get_category_salience,
    remove_dupes,
)
import sg_covid_impact
from sg_covid_impact.getters.companies_house import get_sector
from sg_covid_impact.getters.glass import get_organisation_description
from sg_covid_impact.getters.glass_house import get_glass_house

project_dir = sg_covid_impact.project_dir


_DIV_CODE_DESCRIPTION = extract_sic_code_description(load_sic_taxonomy(), "Division")

def preview(x):
    print(x.head())
    return x


def get_glass_ch_top_matches(gl_ch):
    """Subsets glass-ch to focus on top matches for each glass company
    Args:
        gl_h: glass-ch lookup
    """

    # Find Companies House companies with multiple matches
    gl_multi_matches = (
        gl_ch.groupby("company_number")
        .size()
        .reset_index(name="n_matches")
        .query("n_matches>1")["company_number"]
        .tolist()
    )

    # For those, find the top matching glass org
    gl_top_match = (
        gl_ch.loc[gl_ch["company_number"].isin(gl_multi_matches)]
        .groupby("company_number")
        .apply(lambda x: x.sort_values("score", ascending=False).iloc[0, :])
        .reset_index(drop=True)
    )

    # Combine with the one-matched glass orgs
    gl_unique_matches = pd.concat(
        [gl_ch.loc[~gl_ch["company_number"].isin(gl_multi_matches)], gl_top_match],
        axis=0,
    ).reset_index(drop=True)

    return gl_unique_matches


def make_glass_ch_sectors(glass_descr, glass_ch, ch_sectors, threshold=60):
    """Merges glass descriptions with CH sectors via glass-ch matches
    Args:
        glass_descr (df): glass company descriptions
        glass_ch (df): glass companies house lookup
        ch_sector (df): companies house sectors
        threshold (int): match score threshold
    """

    _DIV_CODE_DESCRIPTION = extract_sic_code_description(
        load_sic_taxonomy(), "Division"

    gl_ch_sector = (
        glass_descr.query("date == '2020-06-01'")
        .merge(glass_ch, left_on="org_id", right_on="org_id")
        .query(f"score > {threshold}")
        .merge(ch_sectors, left_on="company_number", right_on="company_number")
        .assign(division=lambda x: [c[:2] for c in x["SIC4_code"]])
        .assign(division_name=lambda x: x["division"].map(_DIV_CODE_DESCRIPTION))
        .pipe(preview)
    )
    return gl_ch_sector


def make_glass_ch_merged():
    """Creates merged glass - ch dataset"""
    gl_descr = get_organisation_description()
    ch_sector = get_sector()
    gl_ch = get_glass_house()

    gl_descr_sector = make_glass_ch_sectors(
        gl_descr, get_glass_ch_top_matches(gl_ch), ch_sector
    )

    return gl_descr_sector
      
def glass_descr_preprocessing(gl_descr):
    """Preprocesses glass descriptions (ie tokenise, bigram)
    Args:
        gl_desc (df): glass description
    """
    glass_tokenised = glass_w_descr["description"].apply(
        lambda x: clean_and_tokenize(x, remove_stops=True)
    )
    return make_ngram(glass_tokenised, n_gram=2)


def extract_salient_terms(
    glass_descr, tokenised_variable="tokenised_bi", sector="division", word_thres=75
):
    """Extracts salient terms from glass descriptions
    Args:
        glass_descr (str): df with descriptions (raw and tokenised) and sectors
        tokenised_variable (str): name of the variable with tokenised descrs
        sector (str): variable with sector
        word_thres (int): Minimum number of variables to consider
    """
    corpus_freqs = flatten_freq(glass_descr[tokenised_variable])

    # Creates a dict
    sector_salient_words = {
        w: get_category_salience(
            glass_descr, sector, w, tokenised_variable, corpus_freqs, thres=75
        )
        for w in sorted(set(glass_w_descr[sector]))
    }

    return sector_salient_words


def salient_terms_post_process(
    glass_descr,
    sector_salient_words,
    sector="division",
    sector_min=150,
    keywords_n=20,
    stop_keywords=6,
):
    """Post-process salient terms
    Args:
        glass_descr (df): glass descriptions
        sector_salient_words (dict): sector salient words
        sector (str): sector variable
        sector_min (int): minimum number of obs in a sector
        keywords_n (int): Number of keywords to return
        stop_keywords (int): Max number of sectors where a keyword can appear
    """
    sector_counts = glass_descr[sector].value_counts()

    keep_sector = sector_counts.loc[sector_counts > sector_min].index

    # Remove sectors with low activity and duplicate keywords
    salient_no_dupes = {
        k: remove_dupes(v, k)
        for k, v in sector_salient_words.items()
        if k in keep_sector
    }

    # Focus on the top keywords_n by salience in a sector
    _sector_keywords = {
        k: [re.sub("_", " ", x) for x in v.iloc[:keywords_n].index.tolist()]
        for k, v in salient_no_dupes.items()
    }

    # Remove very common terms
    very_common_terms = (
        flatten_freq([v for v in _sector_keywords.values()])
        .reset_index(name="freq")
        .query(f"freq > {stop_keywords}")["index"]
        .tolist()
    )

    sector_keywords = {
        k: [el for el in v if el not in very_common_terms]
        for k, v in _sector_keywords.items()
    }

    return sector_keywords


if __name__ == "__main__":

    logging.info("Reading data")

    _DIV_CODE_DESCRIPTION = extract_sic_code_description(
        load_sic_taxonomy(), "Division"
    gl_descr_sector = make_glass_ch_merged()

    # Identify companies with description and pre-process descriptions
    logging.info("preprocess glass descriptions")
    glass_w_descr = gl_descr_sector.dropna(axis=0, subset=["description"])
    glass_w_descr["tokenised_bi"] = glass_descr_preprocessing(glass_w_descr)

    # Extract salient terms
    logging.info("Extracting salient terms")
    division_salient_words = extract_salient_terms(glass_w_descr)

    # Post-processing
    logging.info("Post-processing salient keywords")
    sector_keywords = salient_terms_post_process(glass_w_descr, division_salient_words)

    with open(
        f"{project_dir}/data/processed/salient_words_selected.p", "wb"
    ) as outfile:
        pickle.dump(sector_keywords, outfile)
    with open(
        f"{project_dir}/data/processed/salient_words_division.p", "wb"
    ) as outfile:
        pickle.dump(division_salient_words, outfile)

