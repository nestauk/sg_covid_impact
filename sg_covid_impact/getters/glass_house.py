# %%
"""Data getter for Glass - Companies House matching."""
import logging

import pandas as pd
from metaflow import namespace

from sg_covid_impact.utils.metaflow import cache_getter_fn, flow_getter
import sg_covid_impact


logger = logging.getLogger(__name__)
namespace(None)


def run_id() -> int:
    """Get `run_id` for flow

    NOTE: This is loaded from __init__.py not from file
    """
    return sg_covid_impact.config["flows"]["glass_house"]["run_id"]


@cache_getter_fn
def get_glass_house() -> pd.DataFrame:
    """Glass - Companies House fuzzy matching."""
    return flow_getter("GlassHouseMatch", run_id=run_id()).company_numbers.rename(
        columns={"sim_mean": "score"}
    )[["org_id", "company_number", "score"]]
