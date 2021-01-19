# %%
"""Data getter (Research DAPS) for National Statistics Postcode Lookup (NSPL)."""
import pandas as pd
from metaflow import namespace

from sg_covid_impact.utils.metaflow import flow_getter, cache_getter_fn
import sg_covid_impact

namespace(None)


def run_id() -> int:
    """Get `run_id` for flow

    NOTE: This is loaded from __init__.py not from file
    """
    return sg_covid_impact.config["flows"]["nspl"]["run_id"]


@cache_getter_fn
def get_nspl() -> pd.DataFrame:
    return flow_getter("NSPL", run_id=run_id()).nspl_data
