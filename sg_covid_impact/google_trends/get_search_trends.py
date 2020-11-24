# %%
import logging
import re
import yaml

import pandas as pd
import toolz.curried as t
from metaflow import Flow

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


if __name__ == "__main__":
    # Load config
    config = sg_covid_impact.config["flows"]["google_search"]["params"]
    threshold = config["term_salience_threshold"]
    anchor_periods = list(config["anchor_periods"].values())

    # Trends for each term over time
    trends = get_trends().assign(variable=lambda x: x.variable.str.replace(" ", "_"))

    # Match trend terms to divisions
    division_trends = (
        load_salient_words()
        .pipe(extract_salient_words, threshold)
        .merge(trends.rename(columns={"variable": "keyword"}), on="keyword", how="left")
    )
