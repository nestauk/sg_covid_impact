# %%

import pandas as pd
import altair as alt
from IPython.display import display

import sg_covid_impact
from sg_covid_impact.sic import section_code_lookup, make_sic_lookups
from sg_covid_impact.getters.companies_house import get_address as CH_address
from sg_covid_impact.getters.glass import get_notice, get_organisation
from sg_covid_impact.getters.glass_house import get_glass_house
from sg_covid_impact.getters.nspl import get_nspl
from sg_covid_impact.queries.sector import get_organisation_SIC_codes
from sg_covid_impact.queries.geography import get_organisation_ids_for_scotland
from sg_covid_impact.descriptive import read_lad_name_lookup

from sg_covid_impact.utils.altair_s3 import export_chart

match_threshold = sg_covid_impact.config["params"]["match_threshold"]
# %%
# LOOKUPS

# Scottish glass id's
scot_ids = get_organisation_ids_for_scotland()

# SIC section names
SIC_section_names = make_sic_lookups()[1]
# %%

nspl = get_nspl().rename(columns={"pcds": "postcode"})[["postcode", "laua"]]
nspl.head()

# %%


notices = get_notice()
notices.head()

# %%

organisations = get_organisation()
organisations.head()

# %%

glasshouse = get_glass_house().query(f"score > {match_threshold}")
glasshouse.head()
# %%

address = CH_address()
address.head()

# %%

org_address = address.merge(glasshouse, on="company_number")[
    ["org_id", "address_text", "postcode"]
].merge(nspl, on="postcode")
org_address.head()

# %%

organisations_by_laua = organisations.merge(
    org_address[["org_id", "laua"]], on="org_id"
).assign(laua_name=lambda x: x.laua.map(read_lad_name_lookup()))
organisations_by_laua.head()

# %%

notices_by_laua = notices.merge(org_address[["org_id", "laua"]], on="org_id").assign(
    laua_name=lambda x: x.laua.map(read_lad_name_lookup())
)
notices_by_laua.head()

# %%

SIC_lookup = (
    get_organisation_SIC_codes(match_threshold)
    .query("rank == 1")[["org_id", "SIC5_code"]]
    .drop_duplicates()
)

# %%

notices_by_section = notices.merge(SIC_lookup, on="org_id").assign(
    section=lambda x: x.SIC5_code.str.slice(0, 2).map(section_code_lookup())
)[["section", "org_id", "notice_id", "date"]]

organisations_by_section = organisations.merge(SIC_lookup, on="org_id").assign(
    section=lambda x: x.SIC5_code.str.slice(0, 2).map(section_code_lookup())
)
# %%

# Count by section
notices_by_section.section.map(SIC_section_names).value_counts().plot.barh()

# %%


def log_x_histogram(data, variable, title=None):
    return (
        alt.Chart(data)
        .transform_calculate(log_x=f"log(datum.{variable})/log(10)")
        .transform_bin("bin_log_x", field="log_x")
        .transform_calculate(
            x1="pow(10, datum.bin_log_x)", x2="pow(10, datum.bin_log_x_end)"
        )
        .mark_bar()
        .encode(
            x=alt.X("x1:Q", scale=alt.Scale(type="log", base=10), title=title),
            x2="x2:Q",
            y=alt.Y("count()", title=None),
        )
    )


data = notices.assign(len=lambda x: x.snippet.str.len())[["len"]].query(
    "len > 0"
)
chart = log_x_histogram(data, "len", "Notice length")
export_chart(chart, "notice_length")

# %%


def relative_proportions(
    organisations: pd.DataFrame, notices: pd.DataFrame, variable: str
) -> pd.DataFrame:
    """."""
    total_dist = (
        organisations[variable].value_counts() / organisations.shape[0]
    ).to_frame("total_proportion")

    notice_dist = (
        notices.groupby([variable, "date"])
        .size()
        .pipe(lambda x: x / x.groupby("date").sum())
    ).to_frame("notice_proportion")

    return (
        total_dist.join(notice_dist.reset_index(level="date"))
        .rename_axis(index=variable)
        .reset_index()
        .assign(
            diff=lambda x: x.total_proportion - x.notice_proportion,
            diff_prop=lambda x: x["diff"] / x.total_proportion,
        )
    )


sector_prop_scotland = relative_proportions(
    organisations_by_section.loc[lambda x: x.org_id.isin(scot_ids)],
    notices_by_section.loc[lambda x: x.org_id.isin(scot_ids)],
    "section",
).assign(
    sector_name=lambda x: x.section.map(SIC_section_names),
)
display(sector_prop_scotland.head())

sector_prop = relative_proportions(
    organisations_by_section, notices_by_section, "section"
).assign(
    sector_name=lambda x: x.section.map(SIC_section_names),
)
display(sector_prop.head())

laua_prop = relative_proportions(organisations_by_laua, notices_by_laua, "laua").assign(
    laua_name=lambda x: x.laua.map(read_lad_name_lookup())
)

display(laua_prop.head())

# %%


def prop_plot(data, variable):
    """Plot proportions of `data` by `variable`."""
    base = alt.Chart(data.assign(base_label="Base Frequency")).encode(
        y=alt.Y(
            f"{variable}:N",
            sort=alt.EncodingSortField(field="diff_prop", op="sum", order="descending"),
        )
    )

    scale_type = "linear"

    base_freq = base.encode(
        x=alt.X("Base proportion:Q", scale=alt.Scale(type=scale_type)),
        shape=alt.Shape("base_label", title=""),
        tooltip=[variable, "Base proportion"],
    ).mark_point(size=100, color="black")

    total = (
        base.transform_fold(
            fold=["Notice proportion"],
            as_=["variable", "value"],
        )
        .encode(
            x=alt.X("value:Q", title="Proportion", scale=alt.Scale(type=scale_type)),
            color=alt.Color(
                "date:N", title="", legend=alt.Legend(formatType="time", format="%B")
            ),
            tooltip=[
                variable,
                alt.Tooltip("date:T", formatType="time", format="%B", title="Month"),
                alt.Tooltip("value:Q", format=".3f", formatType="number"),
            ],
        )
        .mark_square()
    )

    return total + base_freq


# %%

chart = prop_plot(
    laua_prop.rename(
        columns={
            "total_proportion": "Base proportion",
            "notice_proportion": "Notice proportion",
            "laua_name": "Region",
        }
    )
    .loc[lambda x: x.laua.str.startswith("S")]
    .sort_values("diff", ascending=False),
    "Region",
)
export_chart(chart, "notice_proportion_scottish_laua")
chart
# %%
prop_plot(
    sector_prop.rename(
        columns={
            "total_proportion": "Base proportion",
            "notice_proportion": "Notice proportion",
            "sector_name": "SIC section",
        }
    ),
    "SIC section",
)

# %%
prop_plot(
    sector_prop_scotland.rename(
        columns={
            "total_proportion": "Base proportion",
            "notice_proportion": "Notice proportion",
            "sector_name": "SIC section",
        }
    ),
    "SIC section",
)

# %%


def prop_plot_UK_vs_scotland(data, variable):
    """Plot proportions of `data` by `variable` comparing UK and Scotland."""
    base = alt.Chart(data.assign(base_label="Base Frequency")).encode(
        y=alt.Y(
            f"{variable}:N",
            sort=alt.EncodingSortField(field="diff_prop", op="sum", order="descending"),
        )
    )

    scale_type = "linear"

    base_freq = base.encode(
        x=alt.X("Base proportion:Q", scale=alt.Scale(type=scale_type)),
        shape=alt.Shape("country:N", title="Country"),
        tooltip=["country", "Base proportion"],
    ).mark_point(size=100, color="black")

    total = (
        base.transform_fold(
            fold=["Notice proportion"],
            as_=["variable", "value"],
        )
        .encode(
            x=alt.X("value:Q", title="Proportion", scale=alt.Scale(type=scale_type)),
            color=alt.Color(
                "date:N",
                legend=alt.Legend(formatType="time", format="%B", title="Month"),
            ),
            shape=alt.Shape("country:N", title="Country"),
            tooltip=[
                "country",
                alt.Tooltip("date:T", formatType="time", format="%B", title="Month"),
                alt.Tooltip("value:Q", format=".3f", formatType="number"),
            ],
        )
        .mark_point()
    )

    return total + base_freq


data = pd.concat(
    [
        sector_prop_scotland.assign(country="Scotland"),
        sector_prop.assign(country="UK"),
    ]
).rename(
    columns={
        "total_proportion": "Base proportion",
        "notice_proportion": "Notice proportion",
        "sector_name": "SIC section",
    }
)

chart = prop_plot_UK_vs_scotland(data, "SIC section")
export_chart(chart, "uk_vs_scotland_notices_by_section")
chart
