import pandas as pd
import metaflow as mf

import sg_covid_impact


def run_id() -> int:
    """Get `run_id` for flow

    NOTE: This is loaded from __init__.py not from file
    """
    return sg_covid_impact.config["flows"]["google_search"]["run_id"]


def _get_trends(run_id: int) -> pd.DataFrame:
    return mf.Run(f"GoogleTrends/{run_id}").data.output.drop("index", axis=1)


def get_trends() -> pd.DataFrame:
    """Merges latest `run_id`, and the older `run_id_old` with more salient terms."""

    return (
        _get_trends(run_id()).sort_values(["anchor_period", "date", "variable"])
        # Some rows have NaT/nan date and a value of -1 because they couldn't
        # have trends found, drop these:
        .dropna()
        # Drop duplicates (ignoring value column) due to merging two runs
        .drop_duplicates(subset=["date", "anchor_period", "variable"])
    )
