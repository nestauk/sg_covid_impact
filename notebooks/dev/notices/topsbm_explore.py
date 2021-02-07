"""Generates visualisations for Topic modelling analysis."""
# %%
import calendar

import altair as alt
import pandas as pd
from IPython.display import display

from sg_covid_impact.getters.topsbm import get_topsbm_scotland
from sg_covid_impact.topsbm_utils import (
    get_top_words,
    number_topics_and_clusters,
    get_topicdist,
    plot_topic_activity_heatmap,
    normalise_activity_by_sector,
    normalise_activity_by_topic,
    normalise_activity_by_sector_month,
)
from sg_covid_impact.utils.altair_s3 import export_chart
from sg_covid_impact import config
from sg_covid_impact.getters.glass import get_notice
from sg_covid_impact.getters.glass import get_sector as get_glass_sector
from sg_covid_impact.queries.sector import get_organisation_SIC_codes
from sg_covid_impact.sic import (
    extract_sic_code_description,
    load_sic_taxonomy,
    make_sic_lookups,
)
from sg_covid_impact.descriptive import calculate_sector_exposure


alt.data_transformers.disable_max_rows()
match_threshold = config["params"]["match_threshold"]

# %%


def get_sector_labels_section(notices, match_threshold, SIC_section_lookup):
    return (
        get_organisation_SIC_codes(match_threshold)
        .assign(
            sector_name=lambda x: x.SIC5_code.str.slice(0, 4).map(SIC_section_lookup)
        )
        .merge(notices, on="org_id")
    ).set_index("notice_id")[["sector_name"]]


def get_sector_labels_division(notices, match_threshold, SIC_division_lookup):
    return (
        get_organisation_SIC_codes(match_threshold)
        .assign(
            sector_name=lambda x: x.SIC5_code.str.slice(0, 2).map(SIC_division_lookup),
            sector=lambda x: x.SIC5_code.str.slice(0, 2),
        )
        .merge(notices, on="org_id")
    ).set_index("notice_id")[["sector_name", "sector"]]


def get_sector_labels_glass(notices):
    return (
        get_glass_sector()
        # Latest date only
        .pipe(lambda x: x.loc[lambda y: y.date == x.date.max()])
        # Only consider dominant sector
        .query("rank == 1")
        # Convert to notices
        .merge(notices, on="org_id")
    ).set_index("notice_id")[["sector_name"]]


def combine_topics_exposure(
    notices_by_month, topicdist, exposures_ranked, sector_labels_division
):
    """Combine topic activity and exposure rankings - over time and sector."""

    return (
        get_topic_activity_over_time(
            notices_by_month, topicdist, sector_labels_division
        )
        # Normalise
        .pipe(
            normalise_activity_by_sector_month,
            sector_labels_division.loc[lambda x: x.index.isin(titles)].join(
                notices_by_month.set_index("notice_id")
            ),
            "sector_name",
        )
        # Tidy format
        .melt(
            ignore_index=False, var_name="topic_index", value_name="topic_activity"
        ).reset_index()
        # Add exposure
        .merge(
            exposures_ranked[["division_name", "zscore", "month"]].rename(
                columns={"division_name": "sector_name"}
            ),
            on=("sector_name", "month"),
        )
    )


def plot_topic_exposure_correlation(data, topic_index, top_words=None):
    if top_words is not None:
        data = data.assign(top_words=lambda x: x.topic_index.map(top_words))

    return (
        alt.Chart(data.query(f"(topic_index == {topic_index})"))
        .mark_circle()
        .encode(
            x="topic_activity",
            color="sector_name",
            y="zscore",
            tooltip=["topic_index", "sector_name", "zscore", "top_words:N"],
        )
    )


def get_topic_activity_over_time(notices_by_month, topicdist, sector_labels):
    """Topic activity indexed by time."""

    return (
        topicdist.merge(notices_by_month, left_index=True, right_on="notice_id")
        .set_index("notice_id")
        .join(sector_labels)
        .groupby(["sector_name", "month"])
        .sum()
    )


# %%
notices = get_notice()

sector_labels_glass = get_sector_labels_glass(notices)

SIC_division_lookup = extract_sic_code_description(
    load_sic_taxonomy(), "Division"
)  # SIC2 -> Division label
sector_labels_division = get_sector_labels_division(
    notices, match_threshold, SIC_division_lookup
)

SIC_section_lookup = make_sic_lookups()[2]  # SIC4 -> Section label
sector_labels_section = get_sector_labels_section(
    notices, match_threshold, SIC_section_lookup
)

# %%

exposures_ranked = (
    calculate_sector_exposure()[0]
    .assign(month=lambda x: x.month_year.dt.month)
    .query("5 <= month < 8")
)

# %%

# Load topsbm model
o = get_topsbm_scotland()
titles = o["titles"]
model = o["model"]
# %%

model.state.print_summary()
# N: B of level l-1
# B: Number of topics + number of clusters?

# Select level of hierarchy
L = 3
number_topics_and_clusters(model, L)

topics = model.topics(l=L)
top_words = get_top_words(topics)
top_words[0], topics[0]

topicdist = get_topicdist(model, titles, L)

# %%

# What sector hierarchy do we want? Glass / Section / Division...
sector_labels = sector_labels_division.loc[lambda x: x.index.isin(titles)]

topic_activity = sector_labels.join(topicdist).dropna().groupby("sector_name").sum()

# Normalise topic activity
topic_activity_normed = normalise_activity_by_topic(topic_activity)
chart_top = plot_topic_activity_heatmap(topic_activity_normed, top_words)
export_chart(chart_top, f"scotland_div_topic_activity_level_{L}_norm_by_topic")

# Topic activity by sector
topic_activity_normed = normalise_activity_by_sector(topic_activity, sector_labels)
chart_sec = plot_topic_activity_heatmap(topic_activity_normed, top_words)
export_chart(chart_sec, f"scotland_div_topic_activity_level_{L}_norm_by_sector")

display(chart_top)
display(chart_sec)


# %%

# What sector hierarchy do we want? Glass / Section / Division...
# sector_labels = sector_labels_glass.loc[lambda x: x.index.isin(titles)]
sector_labels = sector_labels_section.loc[lambda x: x.index.isin(titles)]

topic_activity = sector_labels.join(topicdist).dropna().groupby("sector_name").sum()

# Normalise topic activity
topic_activity_normed = normalise_activity_by_topic(topic_activity)
chart_top = plot_topic_activity_heatmap(topic_activity_normed, top_words)
export_chart(chart_top, f"scotland_topic_activity_level_{L}_norm_by_topic")

# Topic activity by sector
topic_activity_normed = normalise_activity_by_sector(topic_activity, sector_labels)
chart_sec = plot_topic_activity_heatmap(topic_activity_normed, top_words)
export_chart(chart_sec, f"scotland_topic_activity_level_{L}_norm_by_sector")

display(chart_top)
display(chart_sec)

# %%

notices_by_month = notices.assign(month=lambda x: x.date.dt.month)[
    ["month", "notice_id"]
]
sector_labels_by_month = sector_labels.loc[lambda x: x.index.isin(titles)].join(
    notices_by_month.set_index("notice_id")
)

topic_activity_time_normed = get_topic_activity_over_time(
    notices_by_month, topicdist, sector_labels
).pipe(
    normalise_activity_by_sector_month,
    sector_labels_by_month,
    sector_variable="sector_name",
)
topic_activity_time_normed

# %%

data = combine_topics_exposure(
    notices_by_month, topicdist, exposures_ranked, sector_labels_division
)
# %%
# Correlate topics with exposure ranking
df = data.pivot(
    ["month", "sector_name", "zscore"], "topic_index", "topic_activity"
).reset_index(level="zscore")

corrs_ = []
for month in [5, 6, 7]:
    print(f"Month: {month}")
    corr = (
        df.drop("zscore", 1).loc[month].corrwith(df["zscore"].loc[month]).rename(month)
    )
    print(corr.sort_values())
    corrs_.append(corr)
corrs = pd.concat(corrs_, axis=1).sort_values(5)
del corrs_
print(corrs)

# RESULT: correlation is weak and inconsistent across months

# This analysis is problematic anyway as correlation is just as likely caused
#  by common lanaguage between sectors, as by language talking about exposure

# %%

hist = (  # Histograme of correlations with exposure measures
    alt.Chart(
        corrs.melt().assign(
            variable=lambda x: x.variable.apply(
                lambda month: calendar.month_name[month]
            )
        )
    )
    .mark_bar()
    .encode(
        x=alt.X("value:Q", bin=True, title="Correlation"),
        y=alt.Y("count()", title=""),
        color="variable",
    )
)

# Plot of exposure zscore vs topic activity for highest correlated topic
highest_corr = (
    corrs.melt(ignore_index=False).reset_index().loc[lambda x: x.value.idxmax()]
)
highest_corr_plot = plot_topic_exposure_correlation(
    data.query(f"month == {highest_corr.variable}"), highest_corr.topic_index, top_words
)

# Plot of exposure zscore vs topic activity for lowest correlated topic
lowest_corr = (
    corrs.melt(ignore_index=False).reset_index().loc[lambda x: x.value.idxmin()]
)
lowest_corr_plot = plot_topic_exposure_correlation(
    data.query(f"month == {lowest_corr.variable}"), lowest_corr.topic_index, top_words
)

corr_plot = (
    hist.properties(height=450)
    | (
        highest_corr_plot.properties(title="Highest correlation topic", height=200)
        & lowest_corr_plot.properties(title="Lowest correlation topic", height=200)
    )
).resolve_scale(color="independent")
export_chart(corr_plot, "topic_corr_plot")
corr_plot
# %%

sector_labels = sector_labels_section.loc[lambda x: x.index.isin(titles)]

sector_labels_by_month = sector_labels.loc[lambda x: x.index.isin(titles)].join(
    notices_by_month.set_index("notice_id")
)

topic_activity_time_normed = get_topic_activity_over_time(
    notices_by_month, topicdist, sector_labels
).pipe(
    normalise_activity_by_sector_month,
    sector_labels_by_month,
    sector_variable="sector_name",
)

data = (
    topic_activity_time_normed.melt(
        ignore_index=False, var_name="topic_index", value_name="topic_activity"
    )
    .reset_index()
    .assign(
        top_words=lambda x: x.topic_index.map(top_words),
        month=lambda x: x.month.apply(lambda month: calendar.month_name[month]),
    )
)

punch = (
    alt.Chart(data)
    .mark_circle(filled=False)
    .encode(
        y=alt.Y("sector_name:N", title=None),
        x=alt.X("topic_index:O", title="Topic number"),
        size=alt.Size(
            "topic_activity:Q", legend=alt.Legend(orient="top", title="Topic activity")
        ),
        color=alt.Color(
            "month:N",
            scale=alt.Scale(
                domain=["May", "June", "July"]  # , range=["red", "orange", "yellow"]
            ),
            legend=alt.Legend(orient="top", title="Month"),
        ),
        tooltip=["sector_name", "topic_index", "topic_activity", "month", "top_words"],
    )
)

base = (
    alt.Chart(
        data.assign(sector_abbrev=lambda x: x.sector_name.str.slice(0, 1))
        # 5 top topics for each sector
        .groupby(["sector_name"])
        .apply(
            lambda x: x.sort_values("topic_activity").loc[
                lambda y: y.topic_index.isin(
                    y.topic_index.drop_duplicates(keep="first").tail(5).values
                )
            ]
        )
        .reset_index(drop=True)
    )
    .encode(
        x=alt.X(
            "month:N",
            scale=alt.Scale(domain=["May", "June", "July"], zero=False),
            title=None,
        ),
        y=alt.Y("topic_activity:Q", title="Topic activity"),
        color=alt.Color("topic_index:N", legend=None),
        # size="topic_activity:Q",
        tooltip=["sector_name", "topic_index", "topic_activity", "month", "top_words"],
    )
    .properties(height=75)
)

facet = alt.layer(base.mark_point(), base.mark_line()).facet(
    "sector_abbrev:O", columns=9, bounds="full", title="SIC division"
)

chart = (
    alt.vconcat(punch, facet, bounds="full", center=True)
    .configure_header(title=None)
    .resolve_scale("independent")
    .resolve_axis("independent")
)

export_chart(chart, "topic_trend_by_section")
chart

# %%
