"""Script collecting secondary official data providing additional context
about the situation of local economies in Scotland
"""

import pandas as pd
import sg_covid_impact
import logging
import numpy as np

project_dir = sg_covid_impact.project_dir

_APS_URL = "https://www.nomisweb.co.uk/api/v01/dataset/NM_17_5.data.csv?geography=1811939329...1811939332,1811939334...1811939336,1811939338...1811939497,1811939499...1811939501,1811939503,1811939505...1811939507,1811939509...1811939517,1811939519,1811939520,1811939524...1811939570,1811939575...1811939599,1811939601...1811939628,1811939630...1811939634,1811939636...1811939647,1811939649,1811939655...1811939664,1811939667...1811939680,1811939682,1811939683,1811939685,1811939687...1811939704,1811939707,1811939708,1811939710,1811939712...1811939717,1811939719,1811939720,1811939722...1811939730&date=latestMINUS2&variable=18,45,290,335,344&measures=20599,21001,21002,21003"
_ASHE_URL = "https://www.nomisweb.co.uk/api/v01/dataset/NM_30_1.data.csv?geography=1811939329...1811939332,1811939334...1811939336,1811939338...1811939497,1811939499...1811939501,1811939503,1811939505...1811939507,1811939509...1811939517,1811939519,1811939520,1811939524...1811939570,1811939575...1811939599,1811939601...1811939628,1811939630...1811939634,1811939636...1811939647,1811939649,1811939655...1811939664,1811939667...1811939680,1811939682,1811939683,1811939685,1811939687...1811939704,1811939707,1811939708,1811939710,1811939712...1811939717,1811939719,1811939720,1811939722...1811939730&date=latest&sex=8&item=2&pay=7&measures=20100,20701"
_SIMD_URL = "https://www.gov.scot/binaries/content/documents/govscot/publications/statistics/2020/01/scottish-index-of-multiple-deprivation-2020-ranks-and-domain-ranks/documents/scottish-index-of-multiple-deprivation-2020-ranks-and-domain-ranks/scottish-index-of-multiple-deprivation-2020-ranks-and-domain-ranks/govscot%3Adocument/SIMD%2B2020v2%2B-%2Branks.xlsx"
_DZ_LU = "http://statistics.gov.scot/downloads/file?id=2a2be2f0-bf5f-4e53-9726-7ef16fa893b7%2FDatazone2011lookup.csv"
_SECOND = f"{project_dir}/data/processed/lad_secondary.csv"


def fetch_nomis(url):
    """Fetch Nomis data
    Args:
        url (str): nomis url
    """
    return pd.read_csv(url)


def process_nomis(
    df, indicator_name, value_column, source, indicator_column="MEASURES_NAME"
):
    """Fetch nomis data
    Args:
        df (df): nomis table
        indicator_name (str): name of indicator
        value_column (str): value column
        source (str): data source
        indicator_column (str): column that contains the indicator
    Returns:
        A clean table with secondary data
    """
    return (
        df.query(f"{indicator_column}=='{indicator_name}'")[
            ["DATE", "GEOGRAPHY_NAME", "GEOGRAPHY_CODE", value_column, "OBS_VALUE"]
        ]
        .reset_index(drop=True)
        .rename(columns={"OBS_VALUE": "VALUE", value_column: "VARIABLE"})
        .assign(source=source)
        .rename(columns=str.lower)
    )


def fetch_datazone_lookup():
    """Fetch datazone lookup"""
    logging.info("Fetching SIMD")
    dz_lu = pd.read_csv(_DZ_LU)
    return dz_lu.set_index("DZ2011_Code")["LA_Code"].to_dict()


def simd_population_share_quantiles(
    df, q=np.arange(0, 1.1, 0.1), q_name="decile", high_depr=1
):
    """Calculates share of population in different deprivation deciles
    Args:
        df (df): table with LAD population and SIMD ranking data
        q (q): quantiles to split LADs into (defaults to deciles)
        q_name (str): name for quantile variable
        high_depr (int): Threshold for high deprivation (lower is more deprived)
    Returns a table with share of population in high depr deciles
    """

    # Calculate deciles of deprivation

    df[q_name] = pd.qcut(
        df["SIMD2020v2_Rank"], q=np.arange(0, 1.1, 0.1), labels=False, duplicates="drop"
    )

    simd_agg = df.groupby(["Council_area", "geography_code", q_name])[
        "Total_population"
    ].sum()

    # Calculate shares of the population living in areas with different rankings
    sim_pop_share = (
        simd_agg.reset_index(name="population")
        .pivot_table(
            index=["Council_area", "geography_code"],
            columns=q_name,
            values="population",
        )
        .apply(lambda x: x / x.sum(), axis=1)
    )
    # Sums shares living in high deprivation areas
    sim_high_depr_share = (
        sim_pop_share.loc[:, : high_depr + 1].sum(axis=1).reset_index(name="value")
    )

    return sim_high_depr_share


def fetch_simd():
    """Fetch scottish multiple deprivation index data"""
    return pd.read_excel(_SIMD_URL, sheet_name=1)


def process_simd(df, indices):
    """Processes the Scottish Index of Multiple Deprivation data
    Args:
        df (df): A Scottish Index of Multiple Deprivation table
        indices (list): indices we want to aggregate over
    Returns:
        Table with share of population living in high SIMD areas
    """

    datazone_lad_code_lookup = fetch_datazone_lookup()

    df["geography_code"] = df["Data_Zone"].map(datazone_lad_code_lookup)

    high_depr_share = simd_population_share_quantiles(df)

    # Add some column names etc so we can combine with other secondary data
    high_depr_share = (
        high_depr_share.assign(variable="smd_high_deprivation_share")
        .assign(source="simd")
        .assign(date=2020)
        .rename(columns={"Council_area": "geography_name"})
    )

    return high_depr_share


def read_secondary():
    """REad secondary data"""
    return pd.read_csv(_SECOND)


if __name__ == "__main__":
    ashe = process_nomis(fetch_nomis(_ASHE_URL), "Value", "PAY_NAME", "ashe")
    aps = process_nomis(fetch_nomis(_APS_URL), "Variable", "VARIABLE_NAME", "aps")

    simd = process_simd(fetch_simd(), indices=[0, 1])

    pd.concat([ashe, aps, simd], axis=0).to_csv(_SECOND, index=False)
