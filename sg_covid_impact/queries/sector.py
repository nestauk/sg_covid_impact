# %%
"""Queries relating to Sectors."""
from typing import Set

import pandas as pd

from sg_covid_impact import config
from sg_covid_impact.sic import section_code_lookup
from sg_covid_impact.getters.companies_house import get_sector
from sg_covid_impact.getters.glass import get_notice, get_organisation
from sg_covid_impact.getters.glass_house import get_glass_house

MATCH_THRESHOLD = config["params"]["match_threshold"]
MAX_RANK = 1  # Default to only consider one SIC code per organisation


def get_notice_ids_for_SIC_section(
    section: str, match_threshold: int = MATCH_THRESHOLD, max_rank: int = MAX_RANK
) -> Set[str]:
    """Return notice ID's corresponding to SIC `section`.

    Based on Glass to Companies House matching at `match_threshold`.
    """
    return get_notices_for_SIC_section(
        section, match_threshold, max_rank
    ).notice_id.pipe(set)


def get_notices_for_SIC_section(
    section: str, match_threshold: int = MATCH_THRESHOLD, max_rank: int = MAX_RANK
) -> pd.DataFrame:
    """Return notices corresponding to SIC `section`.

    Based on Glass to Companies House matching at `match_threshold`.
    """
    organisation_ids = get_organisation_ids_for_SIC_section(
        section, match_threshold, max_rank
    )
    return get_notice().loc[lambda x: x.org_id.isin(organisation_ids)]


def get_organisation_ids_for_SIC_section(
    section: str, match_threshold: int = MATCH_THRESHOLD, max_rank: int = MAX_RANK
) -> Set[int]:
    """Return organisation ID's corresponding to SIC `section`.

    Based on Glass to Companies House matching at `match_threshold`.
    """

    return (
        get_glass_house()
        .query(f"score > {match_threshold}")
        .drop("score", axis=1)
        .merge(
            get_sector()
            .assign(
                section=lambda x: x.SIC4_code.str.slice(0, 2).map(section_code_lookup())
            )[["company_number", "rank", "section"]]
            .query(f"section == '{section}' & rank <= {max_rank}"),
            on="company_number",
        )
        .org_id.pipe(set)
    )


def get_organisations_for_SIC_section(
    section: str, match_threshold: int = MATCH_THRESHOLD, max_rank: int = MAX_RANK
) -> pd.DataFrame:
    """Return organisation ID's corresponding to SIC `section`.

    Based on Glass to Companies House matching at `match_threshold`.
    """

    organisation_ids = get_organisation_ids_for_SIC_section(
        section, match_threshold, max_rank
    )
    return get_organisation().loc[lambda x: x.org_id.isin(organisation_ids)]


def get_organisation_SIC_codes(match_threshold: int) -> pd.DataFrame:
    return (
        get_glass_house()
        .query(f"score > {match_threshold}")
        .drop("score", axis=1)
        .merge(
            get_sector(),  # [["company_number", "rank", "section"]]
            on="company_number",
        )[["org_id", "SIC5_code", "rank", "data_dump_date"]]
    )
