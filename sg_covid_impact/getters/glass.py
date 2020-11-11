# %%
import logging
import pandas as pd
from sg_covid_impact.utils.metaflow import flow_getter, cache_getter_fn
import sg_covid_impact


logger = logging.getLogger(__name__)


def run_id() -> int:
    """Get `run_id` for flow

    NOTE: This is loaded from __init__.py not from file
    """
    return sg_covid_impact.config["flows"]["glass"]["run_id"]


GETTER = flow_getter("GlassMergeMainDumpFlow", run_id=run_id())


@cache_getter_fn
def get_organisation() -> pd.DataFrame:
    return GETTER.organisation


@cache_getter_fn
def get_address() -> pd.DataFrame:
    return GETTER.organisationaddress.merge(GETTER.address, on="address_id").drop(
        "address_id", 1
    )


@cache_getter_fn
def get_sector() -> pd.DataFrame:
    return GETTER.organisationsector.merge(GETTER.sector, on="sector_id").drop(
        "sector_id", 1
    )
