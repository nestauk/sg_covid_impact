# %%
"""Script to aggregate NOMIS data over SIC divisions."""
import os
import logging

import pandas as pd

import sg_covid_impact
from sg_covid_impact.getters.nomis import get_BRES, get_IDBR
from sg_covid_impact.sic import (
    load_sic_taxonomy,
    extract_sic_code_description,
    save_sic_taxonomy,
    _SIC_OUTPUT_FILE,
)


project_dir = sg_covid_impact.project_dir


def make_sic_div_lookup(sic):
    """Creates lookup between SIC class and division."""
    return (
        sic.assign(
            Division=lambda x: x.Class.str[0:2],
            Class=lambda x: x.Class.str.replace(".", ""),
        )
        .set_index("Class")["Division"]
        .to_dict()
    )


def aggregate_NOMIS_over_SIC(
    table,
    target_level,
):
    """Aggregates NOMIS table from SIC4 (Class) to `target_level`.

    Args:
        table (`pd.DataFrame`): NOMIS data
        target_level (`str`): target sic level we are converting into

    Returns:
        `pd.DataFrame`
        a table with employment or establishment data by target sic level and geography
    """
    return (
        table.groupby(["geo_cd", "geo_nm", target_level, "year"])["value"]
        .sum()
        .reset_index(drop=False)
    )


if __name__ == "__main__":
    # Ensure SIC data is downloaded
    if not os.path.exists(_SIC_OUTPUT_FILE):
        save_sic_taxonomy()

    NOMIS_FILE_LOC = f"{project_dir}/data/processed/nomis_divisions.csv"

    logging.info("Aggregating NOMIS data over divisions")

    sic = load_sic_taxonomy()
    div_code_description = extract_sic_code_description(sic, "Division")
    sic_div_lookup = make_sic_div_lookup(sic)

    years = [2018, 2019, 2020]

    nomis_divs = []
    for getter, source in zip([get_IDBR, get_BRES], ["idbr", "bres"]):
        nomis_divs.append(
            getter()
            .loc[lambda x: x.year.isin(years)]
            .assign(division=lambda x: x.SIC4.map(sic_div_lookup))
            .pipe(aggregate_NOMIS_over_SIC, target_level="division")
            .assign(
                division_description=lambda x: x.division.map(div_code_description),
                source=source,
            )
        )

    pd.concat(nomis_divs).to_csv(NOMIS_FILE_LOC, index=False)
