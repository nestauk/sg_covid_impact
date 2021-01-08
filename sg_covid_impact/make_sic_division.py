# %%
"""Script to aggregate NOMIS data over SIC divisions."""
import os
import logging

import pandas as pd
import numpy as np

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


def make_section_division_lookup():
    """Creates a lookup between SIC sections and divisions"""
    sic = load_sic_taxonomy()

    # Create a lookup between divisions and sections
    sic["section"] = [
        x.strip() if pd.isnull(x) == False else np.nan for x in sic["SECTION"]
    ]

    section_division_lu = (
        sic[["section", "Division"]]
        .fillna(method="ffill")
        .dropna(axis=0)
        .drop_duplicates(["Division"])
        .set_index("Division")
    ).to_dict()["section"]

    section_name_lookup = (
        sic[["section", "Unnamed: 1"]]
        .dropna()
        .set_index("section")
        .to_dict()["Unnamed: 1"]
    )

    section_name_lookup_long = {k: k + ": " + v for k, v in section_name_lookup.items()}

    return section_division_lu, section_name_lookup_long


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
