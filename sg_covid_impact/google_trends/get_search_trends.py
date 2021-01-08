from pickle import load

import pandas as pd

import sg_covid_impact
from sg_covid_impact.getters.gtab import get_trends


project_dir = sg_covid_impact.project_dir


def load_salient_words() -> pd.DataFrame:
    """Load salient words frequencies.

    PLACEHOLDER!
    """
    return pd.read_csv(f"{project_dir}/data/aux/division_term_freqs.csv", index_col=0)


def extract_salient_words(
    salient_word_df: pd.DataFrame, threshold: float
) -> pd.DataFrame:
    """Extract salient words by division."""
    return salient_word_df.loc[
        lambda df: df.salience >= threshold, ["division", "keyword"]
    ]


def _division_term_lookup_v1() -> pd.DataFrame:
    """division-term lookup from `aux` data."""
    return load_salient_words().pipe(extract_salient_words, threshold)


def _division_term_lookup_v2() -> pd.DataFrame:
    """division-term lookup using `extract_salient_terms.py`."""
    with open(f"{project_dir}/data/processed/salient_words_selected.p", "rb") as fp:
        return (
            pd.Series(load(fp))
            .explode()
            .to_frame("keyword")
            .rename_axis(index="division")
            .reset_index()
        )


def make_division_term_lookup() -> pd.DataFrame:
    """DataFrame giving salient keywords for each division.

    Combines the two sources of salient terms.
    """

    # Match trend terms to divisions (combining the two sources of salience data)
    division_term_lookup1 = _division_term_lookup_v1()

    division_term_lookup2 = _division_term_lookup_v2()

    return division_term_lookup1.append(division_term_lookup2).drop_duplicates()


if __name__ == "__main__":
    # Load config
    config = sg_covid_impact.config["flows"]["google_search"]["params"]
    threshold = config["term_salience_threshold"]
    anchor_periods = list(config["anchor_periods"].values())

    # Trends for each term over time (GTAB)
    trends = get_trends().assign(variable=lambda x: x.variable.str.replace(" ", "_"))

    # Merge GTAB values into division-keyword lookup
    division_trends = (
        make_division_term_lookup()
        .merge(trends.rename(columns={"variable": "keyword"}), on="keyword", how="left")
        .sort_values(["division", "anchor_period", "date", "keyword"])
    )
