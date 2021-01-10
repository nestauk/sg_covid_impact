# %%
import os
import pickle
import logging
import datetime
import requests
import json
import altair as alt
import pandas as pd
import numpy as np
import geopandas as gp
from zipfile import ZipFile
from io import BytesIO


import sg_covid_impact
from sg_covid_impact.make_sic_division import (
    extract_sic_code_description,
    load_sic_taxonomy,
)

project_dir = sg_covid_impact.project_dir


# Utility functions


def zscore(series):
    """Calculate zscore for a variable"""
    m = series.mean(skipna=True)
    st = series.std(skipna=True)
    return [(x - m) / st for x in series]


def make_grouped_share(df, variable, name="share"):
    """Normalise a variable (for using in grouped dfs)"""

    df[name] = df[variable] / df[variable].sum()
    return df


def make_weighted_average(df, weight_var, value_var):
    """Creates a weighted average"""
    return np.sum([r[weight_var] * r[value_var] for _id, r in df.iterrows()])


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


# Reading functions
def read_salience():
    """Reads salience data"""
    with open(f"{project_dir}/data/processed/salient_words_division.p", "rb") as infile:
        sal = pickle.load(infile)

    dfs = []
    for k, v in sal.items():
        v = v.assign(division=k)
        v["freq"] = v[f"{k}_freq"]
        v["salience"] = v[f"{k}_salience"]
        v = v.drop(axis=1, labels=[f"{k}_freq", f"{k}_salience"])
        dfs.append(v)

    return pd.concat(dfs).reset_index(drop=False).rename(columns={"index": "keyword"})


def read_lad_nuts1_lookup():
    """Read a lookup between local authorities and NUTS"""
    lu_df = pd.read_csv(
        "https://opendata.arcgis.com/datasets/3ba3daf9278f47daba0f561889c3521a_0.csv"
    )
    return lu_df.set_index("LAD19CD")["RGN19NM"].to_dict()


def read_claimant_counts():
    """Read claimant ccount data and process it"""
    cl = pd.read_csv(f"{project_dir}/data/processed/claimant_counts.csv")
    cl["date"] = pd.to_datetime(cl["date"])
    cl["month"], cl["year"] = [
        cl["date"].apply(lambda x: getattr(x, p)) for p in ["month", "year"]
    ]
    cl["nuts1"] = cl["geography_code"].apply(assign_nuts1_to_lad)

    return cl


def read_search_trends(stop_words=["love"]):
    """Read search trends"""

    d = pd.read_csv(
        f"{project_dir}/data/processed/term_trends_v2.csv",
        dtype={"division": str},
        parse_dates=["date"],
    )
    d["division_name"] = d["division"].map(_DIVISION_NAME_LOOKUP)
    d["section"] = d["division"].map(_SECTION_DIVISION_LOOKUP)
    d["section_name"] = d["section"].map(_SECTION_NAME_LOOKUP)

    # Focus on terms with dates

    d = d.dropna(axis=0, subset=["date"])

    d["month_year"] = [datetime.datetime(x.year, x.month, 1) for x in d["date"]]
    d["month"], d["year"] = [
        [getattr(x, p) for x in d["date"]] for p in ["month", "year"]
    ]
    d = d.loc[~d["keyword"].isin(stop_words)]

    return d


def read_official(source="bres", year=2019):
    """Read official data
    Args:
        source (str): data source (bres or idbr)
        year (int): year for the data
    """

    div = pd.read_csv(
        f"{project_dir}/data/processed/nomis_divisions.csv", dtype={"division": str}
    )
    official = (
        div.query(f"source=='{source}'").query(f"year=={year}").reset_index(drop=True)
    )
    official["nuts1"] = official["geo_cd"].apply(assign_nuts1_to_lad)
    return official


def fetch_shape():
    """Fetch shapefile data"""

    shape19_url = "https://opendata.arcgis.com/datasets/3a4fa2ce68f642e399b4de07643eeed3_0.zip?outSR=%7B%22latestWkid%22%3A27700%2C%22wkid%22%3A27700%7D"

    shape_path = f"{project_dir}/data/shape/lad_shape_2019/"

    response = requests.get(shape19_url)

    my_zip = ZipFile(BytesIO(response.content))

    my_zip.extractall(shape_path)


def read_shape():
    shape_path = f"{project_dir}/data/shape/lad_shape_2019/"

    shapef = (
        gp.read_file(
            f"{shape_path}/Local_Authority_Districts__December_2019__Boundaries_UK_BUC.shp"
        )
        .to_crs(epsg=4326)
        .assign(id=lambda x: x.index.astype(int))
    )

    return shapef


# Processing functions


def assign_nuts1_to_lad(c):
    """Assigns nuts1 to LAD"""

    if c in _LAD_NUTS1_LOOKUP.keys():
        return _LAD_NUTS1_LOOKUP[c]
    elif c[0] == "S":
        return "Scotland"
    elif c[0] == "W":
        return "Wales"
    elif c[0] == "N":
        return "Northern Ireland"
    else:
        return np.nan


def claimant_count_norm(cl):
    """Normalise claimant count data (2020 months normalised by 2019)
    TODO: Generalise so we can also normalise 2021 months
    """
    cl_norm = (
        cl.query("measure_name == 'Claimants as a proportion of residents aged 16-64'")
        .pivot_table(
            index=["geography_name", "geography_code", "month", "nuts1"],
            columns=["year"],
            values="obs_value",
        )
        .assign(cl_norm=lambda x: x[2020] / x[2019])
        .reset_index(drop=False)
        .drop(axis=1, labels=[2019, 2020])
        .assign(
            date=lambda df: [
                datetime.datetime(2020, x["month"], 1) for r, x in df.iterrows()
            ]
        )
    )

    mean_cl_count = (
        cl_norm.query("month>3").groupby(["geography_code"])["cl_norm"].mean().to_dict()
    )
    cl_norm["mean_cl_count"] = cl_norm["geography_code"].map(mean_cl_count)

    return cl_norm


def search_trend_norm(d):
    """Normalise search trends"""
    pre_post_change = (
        d.query("month!=11")
        .groupby(
            [
                "month_year",
                "keyword",
                "division",
                "year",
                "month",
                "section",
                "section_name",
            ]
        )["value"]
        .mean()
        .reset_index(drop=False)
        .pivot_table(
            index=["keyword", "division", "month", "section_name", "section"],
            columns="year",
            values="value",
        )
        .assign(norm=lambda x: x[2020] / x[2019])
        .reset_index(drop=False)
    )

    pre_post_change.columns = [str(x) for x in pre_post_change.columns]
    # Remove items with zero searches
    pre_post_change = pre_post_change.loc[
        (pre_post_change["2019"] > 0) & (pre_post_change["2020"] > 0)
    ]
    return pre_post_change


<<<<<<< HEAD
def make_weighted_trends(terms, trends):
    """Weights trend data by sector salience and volume"""

    kw_merged = terms.merge(trends, on=["keyword", "division"])
    kw_weighted = (
        kw_merged.assign(value_salience=lambda x: x["salience"] * x["value"])
        .groupby(["division", "month", "year"])
        .apply(
            lambda df: df.assign(
                value_norm=lambda x: x["value_salience"] / x["value_salience"].sum()
            )
        )
        .reset_index(drop=True)
        .query("year==2020")[
            [
                "keyword",
                "division",
                "salience",
                "value",
                "value_salience",
                "value_norm",
                "month",
            ]
        ]
    )
    return kw_weighted


def rank_sector_exposures(trends, sector="division", weighted=True):
=======
def rank_sector_exposures(trends, sector="division", quantile=np.arange(0, 1.1, 0.1)):
>>>>>>> Diversification pipeline
    """Ranks sector exposures to Covid-19
    Args:
        trends (df): normalised keyword trends
        sector (str): sector to calculate exposure for
<<<<<<< HEAD
        approach (str): if we want to calculate a weighted org
=======
        quantile (list): number of segments
>>>>>>> Diversification pipeline
    """

    if weighted == True:
        mean_interest = (
            trends.groupby([sector, "month"])
            .apply(lambda x: make_weighted_average(x, "value_norm", "norm"))
            .reset_index(name="interest_mean")
        )
    else:
        mean_interest = (
            trends.groupby([sector, "month"])["norm"]
            .mean()
            .reset_index(name="interest_mean")
        )

    exposure_rank = (
        mean_interest.groupby("month")
        .apply(
            lambda x: (
                x.assign(zscore=lambda x: zscore(-x["interest_mean"])).assign(
                    rank=lambda x: pd.qcut(
                        x["zscore"],
                        q=quantile,
                        labels=False,
                        duplicates="drop",
                    )
                )
            )
        )
        .reset_index(drop=True)
    )
    return exposure_rank


<<<<<<< HEAD
def calculate_sector_exposure(weighted=True):
    """Calculates sector exposures after some weighting that takes into
    account a term's salience and its search volume
    """
    logging.info("Reading data")
    term_salience = read_salience()
    trends_clean = (read_search_trends()
                    .drop_duplicates(
                        ["keyword", "division", "month", "year"],
                         keep="first"))

    logging.info("Calculating weighted trends")
    kw_weighted = make_weighted_trends(term_salience, trends_clean)
    kw_norm = search_trend_norm(trends_clean)
    kw_weighted_norm = kw_norm.merge(kw_weighted, on=["keyword", "division", "month"])

    logging.info("Calculating Sector exposure")
    exposures_ranked = rank_sector_exposures(kw_weighted_norm, weighted=weighted)
    exposures_ranked["division_name"] = exposures_ranked["division"].map(
        _DIVISION_NAME_LOOKUP
    )

    return exposures_ranked


def make_exposure_shares(exposure_levels, geography="geo_nm"):
=======
def make_exposure_shares(exposure_levels, geography="geo_nm", variable="rank"):
>>>>>>> Diversification pipeline
    """Aggregate shares of activity at different levels of exposure
    Args:
        exposure_levels (df): employment by lad and sector and exposure ranking
        geography (str): geography to aggregate over
        variable (str): variable we want to calculate shares over

    """

    exp_distr = (
        exposure_levels.groupby(["month", variable, geography])["value"]
        .sum()
        .reset_index(drop=False)
        .groupby([geography, "month"])
        .apply(lambda x: x.assign(share=lambda df: df["value"] / df["value"].sum()))
    ).reset_index(drop=True)

    return exp_distr


def make_exposure_shares_detailed(exposure_levels, geo):
    """Calculates detailed exposure shares (at the division level)
    Args:
        exposure_levels (df): table with activity by geo, month, ranking
        geo (str): geographical variable to calculate shares by
    """

    exposure_div_oct_lookup = exposure_levels.set_index(["division_name", "month"])[
        "rank"
    ].to_dict()

    shares_comp = (
        exposure_levels.groupby(["division", "division_name", "month", geo])["value"]
        .sum()
        .reset_index(drop=False)
        .groupby(["month", geo])
        .apply(lambda x: make_grouped_share(x, "value"))
    )

    shares_comp["rank"] = [
        exposure_div_oct_lookup[(x["division_name"], x["month"])]
        for r, x in shares_comp.iterrows()
    ]

    shares_comp["section"] = (
        shares_comp["division"].map(_SECTION_DIVISION_LOOKUP).map(_SECTION_NAME_LOOKUP)
    )
    return shares_comp


def make_high_exposure(exp_shares, level=8, geo="geo_nm"):
    """Subsets exposure share chart to focus on a level
    Args:
        exp_shares (df): exposure shares by geography
        level (int): high exposure threshold
        geo (str): geography to aggregate over
    """
    exp_shares = (
        exp_shares.query(f"rank>{level}")
        .groupby(["month", geo])["share"]
        .sum()
        .reset_index(drop=False)
    )
    return exp_shares


# Plotting functions


def plot_trend_point(
    table,
    geo_var="geography_name",
    x_axis="date",
    y_axis="cl_norm",
    y_title="Claimant count normalised",
    color="mean_cl_count",
    **kwargs,
):
    """Plots a linechart decorated with points to enable selection
    Args:
        table (df): data
        geo_var (str): geography variable (trends to plot)
        x_axis (str): name of x variable
        y_axis (str): name of y variable
        y_title (str): clean Y title
        color (str): name of color variable

    """

    selector = alt.selection_single(fields=[geo_var])

    base = alt.Chart(table).encode(
        x=f"{x_axis}:O",
        y=alt.Y(y_axis, title="Claimant count normalised"),
        tooltip=[geo_var, y_axis],
    )
    point = base.mark_point(filled=True, size=45).encode(
        color=alt.condition(
            selector,
            alt.Color(
                f"{color}:N",
                scale=alt.Scale(scheme="redblue"),
                legend=None,
                sort="descending",
            ),
            alt.value("grey"),
        )
    )
    line = base.mark_line().encode(
        color=alt.condition(
            selector,
            alt.Color(
                f"{color}:N",
                scale=alt.Scale(scheme="redblue"),
                legend=None,
                sort="descending",
            ),
            alt.value("grey"),
        ),
        strokeWidth=alt.condition(selector, alt.value(1.75), alt.value(0.5)),
    )

    chart = (point + line).add_selection(selector).properties(width=300, height=300)

    return chart


def plot_claimant_trend_all_nuts(cl_norm):
    """Plots claimant trends for all NUTS
    Args:
        cl_norm (str): normalised claimant table
    """

    cl_line = (
        alt.Chart(cl_norm)
        .mark_line()
        .encode(
            x="date:T",
            y=alt.Y("cl_norm", title=["Claimant count", "normalised"]),
            color=alt.Color(
                "mean_cl_count:N",
                scale=alt.Scale(scheme="spectral"),
                legend=None,
                sort="descending",
            ),
            tooltip=["geography_name", "cl_norm"],
            facet=alt.Facet(
                "nuts1",
                columns=4,
                sort=alt.EncodingSortField("cl_norm", op="mean", order="descending"),
            ),
        )
        .properties(width=100, height=80)
    )

    return cl_line


def plot_keyword_tends_chart(trends, axis="months"):
    """Plot keyword trends
    Args:
        trends (df): normalised trends by keyword
        axis (str): what variable is in the Y or X axis. If months,
        we have search trends x month with colours for division. If
        sector we have search trends x sector with month for color
    """

    _trends = trends.copy()

    if axis == "sector":
        bubbles = (
            alt.Chart(_trends)
            .transform_filter(alt.datum.norm > 0)
            .mark_point(filled=True, stroke="black", strokeWidth=0.1)
            .encode(
                y=alt.Y(
                    "section_name",
                    title="SIC section",
                    sort=alt.EncodingSortField("mean(norm)"),
                ),
                x=alt.X(
                    "norm",
                    scale=alt.Scale(type="log"),
                    title="Search volume in 2020 normalised by 2019",
                ),
                size=alt.Size("mean(2020)", title="Mean search scale in 2020"),
                color=alt.Color(
                    "month:O",
                    scale=alt.Scale(scheme="spectral"),
                    sort="ascending",
                    title="Month",
                ),
                tooltip=["keyword", "month"],
            )
        ).properties(height=400, width=300)
    else:
        _bubbles = (
            alt.Chart(_trends)
            .transform_filter(alt.datum.norm > 0)
            .mark_point(filled=True, stroke="black", strokeWidth=0.1)
            .encode(
                x=alt.X(
                    "month:O",
                    title="Month",
                    # sort=alt.EncodingSortField('mean(norm)')
                ),
                y=alt.Y(
                    "norm",
                    scale=alt.Scale(type="log"),
                    title=["2020 search volume", "(normalised by 2019)"],
                ),
                size=alt.Size("mean(2020)", title="Mean search volume in 2020"),
                color=alt.Color(
                    "section_name:O",
                    scale=alt.Scale(scheme="spectral"),
                    sort="ascending",
                    legend=alt.Legend(columns=2),
                    title="Section Name",
                ),
                tooltip=["keyword", "section_name", "month"],
            )
        ).properties(height=300, width=400)

        # Add the horizontal
        _trends["v"] = 1

        v = (
            alt.Chart(_trends)
            .mark_rule(strokeWidth=0.5, strokeDash=[1, 1])
            .encode(y=alt.Y("v", scale=alt.Scale(type="log")))
        )

        bubbles = _bubbles + v

    return bubbles


def plot_ranked_exposures(
    ranked, sector="division", title="SIC division", scheme="spectral"
):
    """Plots heatmap with exposure ranks by sector and month
    Args:
        ranked (df): sector exposure ranks by month
        sector (str): sector variable
        title (str): clean sector variable name
    """

    sort_sectors = (
        ranked.groupby(sector)["rank"]
        .mean()
        .sort_values(ascending=False)
        .index.tolist()
    )
    hq = (
        alt.Chart(ranked)
        .mark_rect()
        .encode(
            x=alt.X("month:O"),
            y=alt.Y(f"{sector}:O", sort=sort_sectors, title=title),
            color=alt.Color(
                "rank:Q",
                sort="descending",
                title="Exposure rank",
                scale=alt.Scale(scheme=scheme),
            ),
            tooltip=[sector, f"{sector}_name", "month", "rank"],
        )
        .properties(width=400, height=500)
    )
    return hq


def plot_exposure_evol(exposure_levels, mode="single", geo=None, columns=None):
    """Plot evolution of exposure shares
    Args:
        exposure levels (df): shares in exposure ranking by month
        mode (str): whether we want to plot a single chart or a faceted chart
        geo (str): variable to create facets over (if faceted)
        columns (int): Number of columns for faceted plot

    """

    selector = alt.selection_multi(fields=["rank"])

    exposure_evol = (
        alt.Chart(exposure_levels)
        .mark_area(strokeWidth=0.8)
        .encode(
            x="month:N",
            y=alt.Y("share", scale=alt.Scale(domain=[0, 1])),
            stroke=alt.condition(selector, alt.value("grey"), alt.value("white")),
            tooltip=["rank", "share"],
            color=alt.condition(
                selector,
                alt.Color(
                    "rank:O", scale=alt.Scale(scheme="redblue"), sort="descending"
                ),
                alt.value("lightgrey"),
            ),
        )
    )

    if mode == "faceted":
        geo_sorted = (
            exposure_levels.query("month==10")
            .query("rank>8")
            .groupby(geo)["share"]
            .sum()
            .sort_values(ascending=False)
            .index.tolist()
        )

        output = (
            exposure_evol.encode(facet=alt.Facet(geo, columns=columns, sort=geo_sorted))
            .properties(width=100, height=50)
            .add_selection(selector)
        )

    else:
        output = exposure_evol.properties(width=300, height=200).add_selection(selector)

    return output


def plot_exposure_comparison(exp_levels_comp, month="interactive"):
    """Plot comparing exposure shares in Scotland and rest of UK
    Args:
        exposure_levels_comp (df): exposure levels to compare
        month (str/int): whether to show a single month (int) or create
            interactive plot
    """

    if month != "interactive":
        d = exp_levels_comp.query(f"month=={month}")

        nat_comp = (
            alt.Chart(d)
            .mark_bar(stroke="black", strokeWidth=0.1)
            .encode(
                y=alt.Y(
                    "is_scotland",
                    title=None,
                    scale=alt.Scale(domain=["Scotland", "Not Scotland"]),
                ),
                tooltip=["division_name", "share"],
                x=alt.X("share", title="Employment share"),
                color=alt.Color(
                    "section",
                    legend=alt.Legend(columns=1),
                    scale=alt.Scale(scheme="tableau20"),
                ),
                row=alt.Row("rank:N", title="Exposure rank", spacing=10),
            )
            .properties(height=30, width=200, title=f"Month {month}")
        )

    else:
        slider = alt.binding_range(min=4, max=10, step=1)
        select_month = alt.selection_single(
            name="month", fields=["month"], bind=slider, init={"month": 10}
        )
        nat_comp = (
            alt.Chart(exp_levels_comp)
            .mark_bar(stroke="black", strokeWidth=0.1)
            .encode(
                y=alt.Y(
                    "is_scotland",
                    scale=alt.Scale(domain=["Scotland", "Not Scotland"]),
                    title=None,
                ),
                tooltip=["division_name", "share"],
                x=alt.X("share", title="Employment share"),
                color=alt.Color(
                    "section",
                    legend=alt.Legend(columns=1),
                    scale=alt.Scale(scheme="tableau20"),
                ),
                row=alt.Row("rank:N", title="Exposure rank", spacing=10),
            )
            .properties(height=30, width=200)
            .add_selection(select_month)
            .transform_filter(select_month)
        )

    return nat_comp


def plot_area_composition(exposures, month, area=False, interactive=False):
    """Plot the compositon of an area
    Args:
        exposures (df): exposure shares by sector
        month (str): month to display
        area (str): geography to display
        interactive (bool / str): if False, return static plot. if
            str whether to offer option to select by month or area
    """

    if interactive is False:
        d = exposures.query(f"geo_nm=='{area}'").query(f"month=={month}")
        local_profile = (
            alt.Chart(d, title=f"{area} - month {month}")
            .mark_bar(stroke="white", strokeWidth=0.2)
            .encode(
                y="rank:N",
                x=alt.X("share"),
                tooltip=["division_name"],
                color=alt.Color(
                    "section",
                    legend=alt.Legend(columns=1),
                    scale=alt.Scale(scheme="tableau20"),
                ),
                order=alt.Order("share", sort="descending"),
            )
        ).properties(height=300)
        return local_profile

    if interactive == "area":

        d = exposures.query(f"month == {month}")

        max_x = d.groupby(["rank", "month", "geo_nm"])["share"].sum().max()

        input_dropdown = alt.binding_select(options=list(set(d["geo_nm"])))
        select_place = alt.selection_single(
            name="LAD", fields=["geo_nm"], bind=input_dropdown, init={"geo_nm": area}
        )

        local_profile = (
            alt.Chart(d)
            .mark_bar(stroke="white", strokeWidth=0.2)
            .encode(
                y=alt.Y("rank:N", title="Exposure Rank"),
                x=alt.X(
                    "share",
                    scale=alt.Scale(domain=[0, max_x]),
                    title="Share of employment",
                ),
                tooltip=["division_name", "share"],
                color=alt.Color(
                    "section",
                    title="Section",
                    legend=alt.Legend(columns=1),
                    scale=alt.Scale(scheme="tableau20"),
                ),
                order=alt.Order("share", sort="descending"),
            )
            .add_selection(select_place)
            .transform_filter(select_place)
        ).properties(width=170, height=350)

        return local_profile

    if interactive == "month":

        d = exposures.query(f"geo_nm=='{area}'")

        slider = alt.binding_range(min=4, max=10, step=1)

        select_month = alt.selection_single(
            name="month", fields=["month"], bind=slider, init={"month": 4}
        )

        max_x = d.groupby(["rank", "month"])["share"].sum().max()

        local_profile = (
            alt.Chart(d, title=area)
            .mark_bar(stroke="white", strokeWidth=0.2)
            .encode(
                y="rank:N",
                x=alt.X("share", scale=alt.Scale(domain=[0, max_x])),
                tooltip=["division_name"],
                color=alt.Color(
                    "section",
                    legend=alt.Legend(columns=1),
                    scale=alt.Scale(scheme="tableau20"),
                ),
                order=alt.Order("share", sort="descending"),
            )
            .add_selection(select_month)
            .transform_filter(select_month)
        ).properties(width=200, height=300)
        return local_profile


def plot_choro(
    shapef, count_var, count_var_name, region_name="region", scheme="spectral",
    scale_type='linear'):
    """This function plots an altair choropleth

    Args:
        shapef (json) is the the json version of a geopandas shapefile.
        count_var (str) is the name of the variable we are plotting
        count_var_name (str) tidy name for the count variable
        scale_type (str) is the type of scale we are using. Defaults to log
        region_name (str) is the name of the region variable
        schemes (str) is the colour scheme. Defaults to spectral
    """

    base_map = (  # Base chart with outlines
        alt.Chart(alt.Data(values=shapef["features"]))
        .project(type="mercator")
        .mark_geoshape(filled=False, stroke="gray")
    )

    choropleth = (  # Filled polygons and tooltip
        base_map.transform_calculate(region=f"datum.properties.{region_name}")
        .mark_geoshape(filled=True, stroke="white", strokeWidth=0.1)
        .encode(
            size=f"properties.{count_var}:Q",
            color=alt.Color(
                f"properties.{count_var}:Q",
                title=count_var_name,
                scale=alt.Scale(scheme="spectral",type=scale_type),
                sort="descending",
            ),
            tooltip=[
                "region:N",
                alt.Tooltip(f"properties.{count_var}:Q", format="1.2f"),
            ],
        )
    )

    comb = base_map + choropleth
    return comb



def plot_time_choro(
    sh, exposure_df, month, exposure=8, name="high exposure", exposure_var="rank",
    scale_type='linear'
):
    """Plots exposure choropleth
    Args:
        sh (geodf): shapefile
        exposure_df (df): exposure shares
        month (int): month to visualise
        exposure (int): threshold for high exposure
        name (str): title for exposure variable
        exposure_var (str): name for exposure variable
    """

    selected = exposure_df.query(f"month == {month}").query(
        f"{exposure_var} >= {exposure}"
    )

    merged = sh.merge(selected, left_on="lad19cd", right_on="geo_cd")

    merged_json = json.loads(merged.to_json())


    my_map = plot_choro(merged_json, "share", ["Share of", f"{name}"], "lad19nm",
                        scale_type=scale_type)

    return my_map


# Build some of the parameters we use in the functions
_SHAPE_PATH = f"{project_dir}/data/shape/lad_shape_2019/"
logging.info(_SHAPE_PATH)

_LAD_NUTS1_LOOKUP = read_lad_nuts1_lookup()

_SECTION_DIVISION_LOOKUP, _SECTION_NAME_LOOKUP = make_section_division_lookup()

_DIVISION_NAME_LOOKUP = extract_sic_code_description(load_sic_taxonomy(), "Division")

if os.path.exists(_SHAPE_PATH) is False:
    logging.info("Fetching shapefiles")
    fetch_shape(_SHAPE_PATH)
