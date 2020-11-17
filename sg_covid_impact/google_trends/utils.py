# %%
from gtab import GTAB
import pandas as pd
import logging
import re


def gtab_query(word: str, gtab: GTAB) -> pd.Series:
    word_clean = re.sub("_", " ", word)  # Remove underscores
    try:
        return gtab.new_query(word_clean)["max_ratio"].rename(word_clean)
    except Exception as e:  # Some keywords return an error
        logging.error(e)
        return pd.Series([pd.np.nan], name=word_clean)


def set_gtab_timeframe(gtab: GTAB, anchor_period: str) -> str:
    """Set options on `gtab` returning name of anchorbank."""
    gtab.set_options(pytrends_config={"geo": "GB", "timeframe": anchor_period})
    return anchor_period_to_anchor_filename(anchor_period)


def anchor_period_to_anchor_filename(anchor_period: str) -> str:
    return f"google_anchorbank_geo=GB_timeframe={anchor_period}.tsv"
