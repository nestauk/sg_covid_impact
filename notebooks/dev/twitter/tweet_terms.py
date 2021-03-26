import altair as alt
import pandas as pd
from tweets import tweets

# %%
terms = [
    "covid",
    "lockdown",
    "furlough",
    "open",
    "close",
    "takeaway",
    "collect",
    "delay",
    "supply",
    "brexit",
    "online",
    "deliver",
]
tweets["text"] = tweets.text.str.lower()
for term in terms:
    tweets[term] = tweets.text.str.contains(term)

# %%


def yearly(tweets, year, cols, freq="7d"):
    tweets_ = tweets.loc[lambda x: x.created_at.dt.year == year]
    baseline_month = tweets_.groupby(pd.Grouper(key="created_at", freq=freq)).size()

    return (
        tweets_.groupby(pd.Grouper(key="created_at", freq=freq))[cols]
        .sum()
        .melt(var_name="term", ignore_index=False)
        .join(baseline_month.rename("base"))
        .assign(proportion=lambda x: x.value / x.base)
    )


freq = "7d"
cols = ["open", "close"]
y2019 = (
    yearly(tweets, 2019, cols, freq=freq)
    .loc[lambda x: x.index.month < 12]
    .reindex(fill_value=0)
)
y2020 = yearly(tweets, 2020, cols, freq=freq).reindex(fill_value=0)
# %%

data = y2020.assign(
    norm_value=lambda x: x.proportion
    / y2019.loc[lambda x: x.index.month < 12].proportion.values
)

# Proportion of a months tweets mentioning a term, normalised against 2019
chart = (
    alt.Chart(data.reset_index())
    .mark_line()
    .encode(
        x=alt.X("created_at:T", title=None),
        y=alt.Y("norm_value", title="Frequency relative to month in previous year"),
        color=alt.Color("term:N", title="Tweet term"),
        tooltip=["term", "created_at", "norm_value"],
    )
)
export_chart(chart, "tweets_open_close_norm")
chart

# %%


def foo(tweets, var):
    """Frequency over time, both absolute as proportion."""
    baseline = (
        tweets.groupby([pd.Grouper(key="created_at", freq="1m")])
        .size()
        .to_frame("total")
    )

    return (
        tweets.melt(id_vars=[var, "created_at"], value_vars=terms)  # .sample(10_000)
        .groupby(["variable", var, pd.Grouper(key="created_at", freq="1m")])
        .sum()
        .join(baseline)
        .assign(proportion=lambda x: x.value / x.total)
        .reset_index()
    )


dta = foo(tweets, "section")
dta_place = foo(
    tweets.dropna(subset=["laua"]).loc[lambda x: x.laua.str.startswith("S")], "laua"
)


# %%
chart = (
    alt.Chart(dta)
    .mark_area()
    .encode(
        alt.X(
            "created_at:T",
            axis=alt.Axis(format="%m/%Y"),
            title=None,
        ),
        alt.Y(
            "proportion:Q",
            scale=alt.Scale(type="linear"),
            title=["Proportion of tweets"],
        ),
        alt.Color(
            "variable:N",
            scale=alt.Scale(scheme="category20"),
        ),
        alt.Facet("section:N", columns=2),
        tooltip=["created_at", "value", "proportion", "variable", "section"],
    )
    .properties(width=300, height=100)
    .resolve_scale(y="independent")
    .interactive(bind_y=False)
)
export_chart(chart, "tweet_section_stack_terms")
chart

# %%
# Streamgraph of tweets by industry
chart = (
    alt.Chart(dta)
    .mark_area()
    .encode(
        alt.X(
            "created_at:T",
            axis=alt.Axis(format="%m/%Y"),
            title=None,
        ),
        alt.Y("proportion:Q", title=["Proportion of tweets"]),
        alt.Color("section:N", scale=alt.Scale(scheme="category20b")),
        alt.Facet("variable:N", columns=2, title="Term contained in tweet"),
        tooltip=["created_at", "value", "proportion", "variable", "section"],
    )
    .properties(width=300, height=100)
    .resolve_scale(y="independent")
)

export_chart(chart, "tweet_terms_stack_section")
chart

# %%

# Streamgraph of tweets by region
chart = (
    alt.Chart(dta_place.assign(laua=lambda x: x.laua.map(read_lad_name_lookup())))
    .mark_area()
    .encode(
        alt.X(
            "created_at:T",
            axis=alt.Axis(format="%m/%Y"),
            title=None,
        ),
        alt.Y(
            "proportion:Q",
            stack="zero",
            title=["Proportion of tweets"],
        ),
        alt.Color(
            "laua:N", scale=alt.Scale(scheme="category20b"), title="Council area"
        ),
        alt.Facet("variable:N", columns=2, title="Term contained in tweet"),
        tooltip=["created_at", "value", "proportion", "variable", "laua"],
    )
    .properties(width=300, height=100)
    .resolve_scale(y="independent")
)
export_chart(chart, "tweet_terms_stack_region")
chart

# %%

# Streamgraph of tweets by region
chart = (
    alt.Chart(dta_place.assign(laua=lambda x: x.laua.map(read_lad_name_lookup())))
    .mark_area()
    .encode(
        alt.X(
            "created_at:T",
            axis=alt.Axis(format="%m/%Y"),
            title=None,
        ),
        alt.Y(
            "proportion:Q",
            stack="zero",
            title=["Proportion of tweets"],
        ),
        alt.Color("variable:N", scale=alt.Scale(scheme="category20")),
        alt.Facet("laua:N", columns=3, title="Term contained in tweet"),
        tooltip=["created_at", "value", "proportion", "variable", "laua"],
    )
    .properties(width=300, height=100)
    .resolve_scale(y="independent")
)

export_chart(chart, "tweet_region_stack_terms")
chart
