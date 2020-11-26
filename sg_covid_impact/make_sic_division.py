import os
import re
import logging
import pandas as pd
from sg_covid_impact.getters.nomis import get_BRES, get_IDBR
from sg_covid_impact.sic import load_sic_taxonomy, extract_sic_code_description

import sg_covid_impact

project_dir = sg_covid_impact.project_dir


def make_sic_target_lookup(sic, source_level="Class", target_level="Division"):
    """Makes a lookup between source SIC level (eg class ie SIC-4)
        and a target level (eg Division)
    Args:
        sic (table): the sic taxonomy
        source_level (str): the sic level we are converting from
        target_level: the sic level we want to convert into
    Returns:
        A dict mapping source levels into target levels
    """
    lookup_table = (  # Each row in this lookup has a source and a target
        sic[[target_level, source_level]].fillna(method="ffill").dropna(axis=0)
    )
    # Remove periods from the sic levels
    lookup_table[source_level] = lookup_table[source_level].apply(
        lambda x: re.sub("\\.", "", x)
    )

    return lookup_table.set_index(source_level)[target_level].to_dict()


def convert_sic_data(
    table,
    source_target_lookup,
    code_descr_lookup,
    name,
    source_level="SIC4",
    target_level="division",
):
    """Converts econ activity table from source level (SIC) to target_level
    Args:
        table (pd.DataFrame): official data
        source_target_lookup (dict): lookup between source codes (SIC) and target codes
        code_descr_lookup (dict): lookup between target codes and
            descriptions
        name (str): name for the data source
        source_level (str): name for the source level we are converting from
        target_level (str): target sic level we are converting into
    Returns a table with employment or establishment data by target sic level
        and geography
    """
    table_ = table.copy()

    # Extract division from SIC4s
    table_[target_level] = table_[source_level].map(source_target_lookup)

    table_reg = (  # Aggregate over divisions
        table_.groupby(["geo_cd", "geo_nm", target_level, "year"])["value"]
        .sum()
        .reset_index(drop=False)
    )
    # Add description
    table_reg[f"{target_level}_description"] = table_reg[target_level].map(
        code_descr_lookup
    )
    table_reg["source"] = name

    return table_reg


def get_transform_nomis_data(
    getter,
    years,
    data_source,
    code_descr_lookup,
    source_target_lookup,
    source_level="SIC4",
    target_level="division",
):
    """Gets and subsets nomis data
    Args:
        getter (nomis getter): class to get data from Nesta
        years (list): list of years to consider
        data_source (str): data source name
        code_descr_lookup (dict): lookup between codes codes and descriptions

        target_name (str): target sic category we are converting into
    Returns:
        Table with results by division
    """
    # Get and subset the data
    d = getter()
    d = d.loc[d["year"].isin(years)]
    d_div = convert_sic_data(d, source_target_lookup, code_descr_lookup, data_source)

    return d_div


if __name__ == "__main__":

    NOMIS_FILE_LOC = f"{project_dir}/data/processed/nomis_divisions.csv"

    if not os.path.exists(NOMIS_FILE_LOC):
        logging.info("Converting sic-4 to divisions")

        sic = load_sic_taxonomy()

        # Create div-description lookup
        div_code_description = extract_sic_code_description(sic, "Division")

        # Create sic - div lookup
        sic_div_lookup = make_sic_target_lookup(sic)

        years = [2018, 2019, 2020]

        nomis_divs = []

        for t, source in zip([get_IDBR, get_BRES], ["idbr", "bres"]):
            t_div = get_transform_nomis_data(
                t, years, source, div_code_description, sic_div_lookup
            )
            nomis_divs.append(t_div)

        pd.concat(nomis_divs).to_csv(NOMIS_FILE_LOC, index=False)
    else:
        logging.info("Already converted sic-4 to divisions")
