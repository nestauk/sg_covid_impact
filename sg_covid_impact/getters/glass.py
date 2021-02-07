# %%
"""Data getters for Glass business website data."""
import logging
from typing import Dict, List

import pandas as pd
from metaflow import namespace

from sg_covid_impact.utils.metaflow import flow_getter, cache_getter_fn
import sg_covid_impact


logger = logging.getLogger(__name__)
namespace(None)


def run_id() -> int:
    """Get `run_id` for flow

    NOTE: This is loaded from __init__.py not from file
    """
    return sg_covid_impact.config["flows"]["glass"]["run_id"]


GETTER = flow_getter("GlassMergeMainDumpFlow", run_id=run_id())


def notice_run_id() -> int:
    """get `run_id` for flow

    note: this is loaded from __init__.py not from file
    """
    return sg_covid_impact.config["flows"]["glass_notice"]["run_id"]


NOTICE_GETTER = flow_getter("GlassMergeNoticesDumpFlow", run_id=notice_run_id())


@cache_getter_fn
def get_organisation() -> pd.DataFrame:
    """Glass organisations."""
    return GETTER.organisation


@cache_getter_fn
def get_address() -> pd.DataFrame:
    """Address information extracted from Glass websites (longitudinal)."""
    return GETTER.organisationaddress.merge(GETTER.address, on="address_id").drop(
        "address_id", 1
    )


@cache_getter_fn
def get_sector() -> pd.DataFrame:
    """Sector (LinkedIn taxonomy) information for Glass Businesses(longitudinal)."""
    return GETTER.organisationsector.merge(GETTER.sector, on="sector_id").drop(
        "sector_id", 1
    )


@cache_getter_fn
def get_organisation_description() -> pd.DataFrame:
    """Description of business activities for Glass businesses (longitudinal)."""
    return GETTER.organisationdescription


@cache_getter_fn
def get_organisation_metadata() -> pd.DataFrame:
    """Metadata for Glass businesses (longitudinal)."""
    return GETTER.organisationmetadata


@cache_getter_fn
def get_notice() -> pd.DataFrame:
    """Covid notices for Glass businesses (longitudinal)."""
    return NOTICE_GETTER.notices.rename(columns={"id_organisation": "org_id"})


@cache_getter_fn
def get_covid_term() -> pd.DataFrame:
    """Covid notice terms for each notice for Glass businesses."""
    return NOTICE_GETTER.term


@cache_getter_fn
def get_notice_tokens() -> Dict[str, List[str]]:
    """Tokenised Covid notices."""

    run_id = sg_covid_impact.config["flows"]["notice_tokens"]["run_id"]
    return flow_getter("NoticeTokeniseFlow", run_id=run_id).docs
