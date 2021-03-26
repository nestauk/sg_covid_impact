# Scrip to validate glass data

import pandas as pd
import json
import numpy as np
import os
import logging
import requests
from zipfile import ZipFile
from io import BytesIO
import altair as alt
from sg_covid_impact.getters.glass_house import get_glass_house
from sg_covid_impact.getters.companies_house import get_address, get_sector
from sg_covid_impact.make_sic_division import (
    load_sic_taxonomy,
    extract_sic_code_description,
)
from sg_covid_impact.descriptive import (
    assign_nuts1_to_lad,
    read_shape,
    plot_choro,
    read_lad_nuts1_lookup,
    make_section_division_lookup,
)
from sg_covid_impact.utils.altair_save_utils import (
    google_chrome_driver_setup,
    save_altair,
)
from sg_covid_impact.utils.altair_s3 import export_chart

import sg_covid_impact

project_dir = sg_covid_impact.project_dir

FIG_PATH = f"{project_dir}/figures/scotland"

driver = google_chrome_driver_setup()

nspl_target = f"{project_dir}/data/raw/nspl"
nspl_location = os.path.join(nspl_target, "Data", "NSPL_NOV_2020_UK.csv")
meta_location = os.path.join(nspl_target, "Documents")

# Functions
def make_glass_meta(companies, score=60):
    """Makes the glass metadata table"""
    logging.info("Making glass metadata")
    glass_house = get_glass_house()

    glass_ch_meta = glass_house.query(f"score>{score}").merge(
        companies, on="company_number"
    )

    return glass_ch_meta


def make_companies():
    """Make the companies house table"""
    logging.info("Making CH")
    companies_address = get_address()
    companies_sector = get_sector()

    companies = (
        companies_address[["company_number", "postcode"]]
        .merge(
            companies_sector.query("rank==1")[["company_number", "SIC4_code"]],
            on="company_number",
        )
        .assign(division=lambda x: [c[:2] for c in x["SIC4_code"]])
        .assign(division_name=lambda x: x["division"].map(_DIV_NAME_LOOKUP))
        .merge(nspl, left_on="postcode", right_on="pcds")
    )

    return companies


def fetch_nspl():
    """Fetch NSPL (if needed)"""
    nspl_url = "https://www.arcgis.com/sharing/rest/content/items/4df8a1a188e74542aebee164525d7ca9/data"

    if os.path.exists(nspl_target) is True:
        logging.info("Already collected NSPL")
    else:
        os.makedirs(nspl_target, exist_ok=True)
        req = requests.get(nspl_url)
        zipf = ZipFile(BytesIO(req.content)).extractall(nspl_target)


def make_lad_lookup(geo_var_name="LAD20"):
    """Lookup between LAD names and codes 2020"""
    name_lu = pd.read_csv(
        os.path.join(meta_location, "LA_UA names and codes UK as at 04_20.csv")
    )
    name_dict = name_lu.set_index(f"{geo_var_name}CD")[f"{geo_var_name}NM"].to_dict()
    return name_dict


def read_nspl(
    geo="laua", names="LA_UA names and codes UK as at 04_20.csv", geo_var_name="LAD20"
):
    """Read and tag NSPL"""
    logging.info("Reading NSPL")
    nspl = pd.read_csv(nspl_location, usecols=["pcds", geo]).dropna(
        axis=0, subset=[geo]
    )

    name_lu = pd.read_csv(os.path.join(meta_location, names))

    name_dict = name_lu.set_index(f"{geo_var_name}CD")[f"{geo_var_name}NM"].to_dict()

    nspl[f"{geo}_name"] = nspl[geo].map(name_dict)

    nspl["nuts1"] = nspl[geo].apply(assign_nuts1_to_lad)

    return nspl


def make_shares_comparison(glass, ch, variable):
    """Compare distributions between Glass and CH"""
    out = (
        pd.concat(
            [df[[variable]].value_counts(normalize=True) for df in [glass, ch]], axis=1
        )
        .rename(columns={0: "glass", 1: "companies"})
        .assign(share_norm=lambda x: (x["glass"] / x["companies"]) - 1)
    )
    return out


fetch_nspl()

# Lookups
_DIV_NAME_LOOKUP = extract_sic_code_description(load_sic_taxonomy(), "Division")
_SECTION_DIVISION_LOOKUP, _SECTION_NAME_LOOKUP = make_section_division_lookup()
_LAD_NUTS1_LOOKUP = read_lad_nuts1_lookup()
_LAD_NAME_DICT = make_lad_lookup()

# Read everything
nspl = read_nspl()
companies = make_companies()
glass_meta = make_glass_meta(companies)


# Focus on Scotland
# Scot
glass_meta_sc, companies_sc = [
    df.query("nuts1=='Scotland'").reset_index(drop=True)
    for df in [glass_meta, companies]
]

sector_shares = (
    make_shares_comparison(glass_meta_sc, companies_sc, "division")
    .reset_index(drop=False)
    .assign(
        section_name=lambda x: x["division"]
        .map(_SECTION_DIVISION_LOOKUP)
        .map(_SECTION_NAME_LOOKUP)
    )
    .dropna(axis=0)
)

# Calculate correlations
sector_shares[["glass", "companies"]].corr()

# Sorted divisions
sorted_divs = sector_shares.sort_values(
    ["section_name", "share_norm"], ascending=[True, False]
)["division"].to_list()

sector_shares["division_name"] = sector_shares["division"].map(_DIV_NAME_LOOKUP)

# Chart comparing sector distributions
sector_comparison_chart = (
    alt.Chart(sector_shares)
    .mark_bar()
    .encode(
        y=alt.Y("division", sort=sorted_divs, axis=alt.Axis(labels=False, ticks=False)),
        x=alt.X("share_norm", title="Glass vs CH share"),
        color=alt.Color("section_name", title="Section"),
        tooltip=["division_name"],
    )
).properties(height=300, width=150)
sector_comparison_chart

save_altair(
    sector_comparison_chart, "glass_sector_validation", driver=driver, path=FIG_PATH
)
export_chart(sector_comparison_chart, "glass_sector_validation")

# Chart comparing geo distributions
sh = read_shape()

lad_shares = make_shares_comparison(glass_meta_sc, companies_sc, "laua")

lad_shares[["glass", "companies"]].corr()

merged = sh.merge(
    lad_shares.reset_index(drop=False), left_on="lad19cd", right_on="laua"
)

merged_json = json.loads(merged.to_json())

glass_share_map = (
    plot_choro(
        merged_json, "share_norm", "Glass vs CH share", "lad19nm", scale_type="linear"
    )
    # .configure_view(strokeWidth=0)
    .properties(height=300, width=200)
)

glass_validation = alt.hconcat(sector_comparison_chart, glass_share_map)
glass_validation

save_altair(glass_validation, "glass_place_validation", driver, path=FIG_PATH)
export_chart(glass_validation, "glass_place_validation")

# LAD by division coverage
lad_sector_shares = (
    pd.concat(
        [
            df.groupby("laua").apply(
                lambda x: x["division"].value_counts(normalize=True)
            )
            for df, name in zip([glass_meta_sc, companies_sc], ["glass", "ch"])
        ],
        axis=1,
    )
).fillna(0)
lad_sector_shares.columns = ["glass", "ch"]

lad_sector_shares = (
    lad_sector_shares.assign(share_norm=lambda x: x["glass"] / x["ch"])
    .reset_index(drop=False)
    .rename(columns={"level_1": "division"})
    .assign(division_name=lambda x: x["division"].map(_DIV_NAME_LOOKUP))
    .assign(lad_name=lambda x: x["laua"].map(_LAD_NAME_DICT))
)

corr_list = []

for x in set(lad_sector_shares["laua"]):
    sel = lad_sector_shares.query(f"laua=='{x}'")
    corr = np.float(sel[["glass", "ch"]].corr().iloc[0, 1])
    corr_list.append([x, corr])

lads_corr_dict = {k[0]: k[1] for k in corr_list}
lads_sorted = [x[0] for x in sorted(corr_list, key=lambda x: x[1], reverse=True)]

lads_corr_df = pd.DataFrame(corr_list, columns=["lad_name", "glass_ch_correlation"])

# Plot
rep_chart = (
    alt.Chart(lad_sector_shares)
    .transform_filter(alt.datum.share_norm > 0)
    .mark_rect()
    .encode(
        y=alt.Y("lad_name", sort=lads_sorted, title="Local Authority"),
        x=alt.X("division", axis=alt.Axis(labels=False, ticks=False)),
        color=alt.Color(
            "share_norm",
            sort="descending",
            title="Glass vs CH share",
            scale=alt.Scale(scheme="Spectral", type="log"),
            legend=alt.Legend(orient="bottom"),
        ),
        tooltip=["lad_name", "division_name", "share_norm"],
    )
).properties(width=400, height=300)

corr_chart = (
    alt.Chart(lads_corr_df)
    .mark_point(filled=True, stroke="black", strokeWidth=0.2)
    .encode(
        y=alt.Y(
            "lad_name",
            title=None,
            sort=lads_sorted,
            axis=alt.Axis(labels=False, ticks=False, grid=True),
        ),
        x=alt.X("glass_ch_correlation", title=["Glass-CH sector", "share correlation"]),
        color=alt.Color("glass_ch_correlation", legend=None),
    )
).properties(width=100, height=300)

lad_share_comparison = alt.hconcat(rep_chart, corr_chart, spacing=1).resolve_scale(
    color="independent"
)

save_altair(
    lad_share_comparison, "glass_sector_place_validation", driver=driver, path=FIG_PATH
)
export_chart(lad_share_comparison, "glass_sector_place_validation")
