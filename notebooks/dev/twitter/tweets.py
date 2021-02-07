"""

- 21st April 2019 was easter - reason for close/open spike
- See similar seasonality around xmas

Important to look at proportions of tweets in a given week
(rather than absolute numbers).


Need to better filter out bad matches:
- gretathunberg 11253040 - electriccarhome.co.uk
- livenationuk
- instagram
- skynews
"""
# %%
import altair as alt
import matplotlib.pyplot as plt
import pandas as pd
import toolz.curried as t

from sg_covid_impact.getters.twitter import get_glass_tweets
from sg_covid_impact.queries.sector import get_organisation_SIC_codes
from sg_covid_impact.queries.geography import (
    get_scottish_address_ids,
    get_organisation_laua,
)
from sg_covid_impact.sic import make_sic_lookups
from sg_covid_impact.descriptive import read_lad_name_lookup
from sg_covid_impact.utils.altair_s3 import export_chart

alt.data_transformers.disable_max_rows()

# %%


_, section_description_lookup, sic_section_lookup = make_sic_lookups()

org_sections = (
    get_organisation_SIC_codes(70)
    .assign(section=lambda x: x.SIC5_code.str.slice(0, 4).map(sic_section_lookup))
    .query("rank == 1")[["org_id", "section"]]
    .drop_duplicates()
    .dropna()
)


# %%

tweets = (
    get_glass_tweets()
    .loc[lambda x: (x.created_at.dt.year == 2019) | (x.created_at.dt.month < 12)]
    .merge(org_sections, on="org_id", how="left")
    .merge(get_organisation_laua(), on="org_id", how="left")
)

# %%

# Tweets from accounts tweeting in Jan 2019
tweets2 = tweets.groupby("user").filter(
    lambda x: (x.created_at.min() < pd.Timestamp(year=2019, day=1, month=2, tz="UTC"))
)
# %%

# Tweets from accounts tweeting in Nov 2020
tweets23 = tweets.groupby("user").filter(
    lambda x: (x.created_at.max() >= pd.Timestamp(year=2020, day=1, month=11, tz="UTC"))
)
# %%

# Tweets from accounts tweeting in Jan 2019 and Nov 2020
tweets3 = tweets.groupby("user").filter(
    lambda x: (x.created_at.min() < pd.Timestamp(year=2019, day=1, month=2, tz="UTC"))
    & (x.created_at.max() >= pd.Timestamp(year=2020, day=1, month=11, tz="UTC"))
)

# %%

data = []
titles = [
    "All tweets",
    "Tweeted in Jan 2019",
    "Tweeted in Nov 2020",
    "Tweeted in Jan 2019 & November 2020",
]
for title, tdata in zip(
    titles,
    [tweets, tweets2, tweets23, tweets3],
):
    data.append(
        tdata.groupby(pd.Grouper(key="created_at", freq="1w", label="right"))
        .size()
        .to_frame("count")
        # .reset_index()
        .assign(variable=title)
    )
# %%

chart = (
    alt.Chart(pd.concat(data).reset_index())
    .mark_line()
    .encode(
        x=alt.X("created_at:T", title=None, axis=alt.Axis(format="%m/%Y")),
        y=alt.Y("count:Q"),
        color=alt.Color("variable:N", title=None),
    )
    .properties()
)
export_chart(chart, "tweets_volume")
chart
# %%
# %%

# Number of tweets over time by laua
data = (
    tweets3.groupby(["laua", pd.Grouper(key="created_at", freq="1w", label="right")])
    .size()
    .to_frame("count")
    .reset_index()
    .loc[lambda x: x.laua.str.startswith("S")]
    .assign(laua=lambda x: x.laua.map(read_lad_name_lookup()))
    .dropna(subset=["laua"])
)

chart = (
    alt.Chart(data)
    .transform_joinaggregate(total="sum(count)", groupby=["created_at"])
    .transform_calculate(frac=alt.datum.count / alt.datum.total)
    .mark_area()
    .encode(
        x=alt.X("created_at:T", title=None),
        y=alt.Y("count:Q", stack="zero", title="Number of tweets"),
        color=alt.Color("laua:N", scale=alt.Scale(scheme="category20b")),
        tooltip=["created_at", "laua", "count"],
    )
    .interactive(bind_y=False)
    | alt.Chart(data)
    .transform_joinaggregate(total="sum(count)", groupby=["created_at"])
    .transform_calculate(frac=alt.datum.count / alt.datum.total)
    .mark_area()
    .encode(
        x=alt.X("created_at:T", title=None),
        y=alt.Y("count:Q", stack="normalize", title="Proportion of tweets"),
        color=alt.Color("laua:N", scale=alt.Scale(scheme="category20b")),
        tooltip=["created_at", "laua", alt.Tooltip("frac:Q", format=".1%")],
    )
    .interactive(bind_y=False)
)
export_chart(chart, "tweets_volume_stack_laua")
chart
# %%

# Number of tweets over time by section
data = (
    tweets3.groupby(["section", pd.Grouper(key="created_at", freq="1w", label="right")])
    .size()
    .to_frame("count")
    .reset_index()
)

chart = (
    alt.Chart(data)
    .transform_joinaggregate(total="sum(count)", groupby=["created_at"])
    .transform_calculate(frac=alt.datum.count / alt.datum.total)
    .mark_area()
    .mark_area()
    .encode(
        x=alt.X("created_at:T", title=None),
        y=alt.Y("count:Q", stack="zero", title="Number of tweets"),
        color=alt.Color("section:N", scale=alt.Scale(scheme="category20b")),
        tooltip=["created_at", "section", "count"],
    )
    .interactive(bind_y=False)
    | alt.Chart(data)
    .transform_joinaggregate(total="sum(count)", groupby=["created_at"])
    .transform_calculate(frac=alt.datum.count / alt.datum.total)
    .mark_area()
    .mark_area()
    .encode(
        x=alt.X("created_at:T", title=None),
        y=alt.Y("count:Q", stack="normalize", title="Proportion of tweets"),
        color=alt.Color("section:N", scale=alt.Scale(scheme="category20b")),
        tooltip=["created_at", "section", alt.Tooltip("frac:Q", format=".1%")],
    )
    .interactive(bind_y=False)
)
export_chart(chart, "tweets_volume_stack_section")
chart

# Few accomodation and food services because they probably aren't in CH?

# %%

# Tweets per user - pretty heavy tailed.
# Some way above the ~3000 limit of the twitter API! BECAUSE multiple matches!
def tweets_per_user(tweets, title=None):
    data = (
        tweets.sort_values("org_id")
        .drop_duplicates(subset=["id", "user"])
        .groupby("user")
        .size()
        .to_frame("count")
        .reset_index()
    )

    return (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X(
                "count:Q",
                title="Number of tweets by user",
                scale=alt.Scale(zero=False, domain=(2.0, 3200.0), type="log"),
            ),
            y=alt.Y("count():Q", title="Number of users"),
        )
        .properties(title=title)
    )


chart = tweets_per_user(tweets, title="All tweets") | tweets_per_user(
    tweets3, title="Tweets from accounts tweeting in Jan 2019 and Nov 2020"
)
export_chart(chart, "tweets_per_user")
chart
# %%

# Geo distribution of tweets compared to glass representation
# TODO: do this by user accounts too!
glass_prop = (
    get_organisation_laua()
    .dropna()
    .loc[lambda x: x.laua.str.startswith("S")]
    .laua.value_counts(dropna=True)
    .to_frame("value")
    .rename_axis(index="laua")
    .reset_index()
    .assign(glass_proportion=lambda x: x.value / x.value.sum())
)

data = (
    tweets.drop_duplicates(subset=["org_id"])
    .dropna(subset=["laua"])
    .loc[lambda x: x.laua.str.startswith("S")]
    .laua.value_counts(dropna=True)
    .to_frame("value")
    .rename_axis(index="laua")
    .reset_index()
    .assign(proportion=lambda x: x.value / x.value.sum())
    .merge(glass_prop.drop("value", 1), on="laua")
    .drop("value", 1)
    .assign(rate=lambda x: x.proportion / x.glass_proportion)
    .assign(laua=lambda x: x.laua.map(read_lad_name_lookup()))
)
twitter_prop = (
    alt.Chart(data)
    .mark_bar()
    .encode(
        x=alt.X("proportion:Q", title="Proportion"),
        y=alt.Y("laua:N", title=None),
        color=alt.Color(
            "rate",
            title=["Over-representation", "factor"],
            scale=alt.Scale(scheme="redblue", domainMid=1),
        ),
    )
)

tick = (
    alt.Chart(data)
    .mark_tick(color="black")
    .encode(
        x=alt.X("glass_proportion:Q", title="Proportion"),
        y=alt.Y("laua:N", title=None),
    )
)


export_chart(twitter_prop + tick, "tweets_laua_representivity")
twitter_prop + tick

# %%

# Industry distribution of tweets compared to glass representation
# TODO: do this by user accounts too!
glass_prop = (
    org_sections.loc[lambda x: x.org_id.isin(get_scottish_address_ids())]
    .section.value_counts(dropna=True)
    .to_frame("value")
    .rename_axis(index="section")
    .reset_index()
    .assign(glass_proportion=lambda x: x.value / x.value.sum())
)

data = (
    tweets.drop_duplicates(subset=["org_id"])
    .section.value_counts(dropna=True)
    .to_frame("value")
    .rename_axis(index="section")
    .reset_index()
    .assign(proportion=lambda x: x.value / x.value.sum())
    .merge(glass_prop.drop("value", 1), on="section")
    .drop("value", 1)
    .assign(rate=lambda x: x.proportion / x.glass_proportion)
)
twitter_prop = (
    alt.Chart(data)
    .mark_bar()
    .encode(
        x=alt.X("proportion:Q", title="Proportion"),
        y=alt.Y("section:N", title=None),
        color=alt.Color(
            "rate",
            title=["Over-representation", "factor"],
            scale=alt.Scale(scheme="redblue", domainMid=1),
        ),
    )
)

tick = (
    alt.Chart(data)
    .mark_tick(color="black")
    .encode(
        x=alt.X("glass_proportion:Q", title="Proportion"),
        y=alt.Y("section:N", title=None),
    )
)


export_chart(twitter_prop + tick, "tweets_section_representivity")
twitter_prop + tick


# %%

# Last tweet distribution
data = (
    tweets.dropna(subset=["section"])
    .groupby("user")[["section", "created_at"]]
    .max()
    .loc[lambda x: (x.created_at.dt.year == 2019) | (x.created_at.dt.month < 12)]
    .groupby(["section", pd.Grouper(key="created_at", freq="1m")])
    .size()
    .to_frame("count")
    .reset_index()
)

chart = (
    alt.Chart(data)
    .mark_bar()
    .encode(
        x=alt.X("yearmonth(created_at):T", title="Date of last tweet"),
        y=alt.Y("count", scale=alt.Scale(type="sqrt"), title="Count"),
        color=alt.Color("section:N", scale=alt.Scale(scheme="category20b")),
        tooltip=["created_at:T", "section", "count"],
    )
)

export_chart(chart, "tweets_last_tweet")
chart
# %%

# Prop still active
data.groupby('created_at').sum().assign(prop=lambda x: x["count"]/ x["count"].sum())
