# %%
from sg_covid_impact.utils.metaflow import flow_getter, cache_getter_fn
import sg_covid_impact
import pandas as pd


def run_id() -> int:
    """Get `run_id` for flow

    NOTE: This is loaded from __init__.py not from file
    """
    return sg_covid_impact.config["flows"]["nomis"]["run_id"]


GETTER = flow_getter("Nomis", run_id=run_id())


@cache_getter_fn
def get_IDBR() -> pd.DataFrame:
    return GETTER.IDBR


@cache_getter_fn
def get_BRES() -> pd.DataFrame:
    return GETTER.BRES
