# %%
import altair as alt
import matplotlib.pyplot as plt
import pandas as pd
import toolz.curried as t

from sg_covid_impact.getters.twitter import *  # get_glass_twitter_user_info
from sg_covid_impact.utils.altair_s3 import export_chart

alt.data_transformers.disable_max_rows()
# pd.set_option("plotting.backend", "altair")  # Installing altair_pandas registers this.

# %%

from sg_covid_impact.queries.sector import get_organisation_SIC_codes
from sg_covid_impact.queries.geography import get_scottish_address_ids
from sg_covid_impact.sic import make_sic_lookups

_, section_description_lookup, sic_section_lookup = make_sic_lookups()

org_sections = (
    get_organisation_SIC_codes(70)
    .assign(section=lambda x: x.SIC5_code.str.slice(0, 4).map(sic_section_lookup))
    .query("rank == 1")[["org_id", "section"]]
    .drop_duplicates()
    .dropna()
)
# %%

users = get_glass_twitter_user_info().merge(org_sections, on="org_id", how="left")
users.shape

# %%

users.head(2).T

# %%

# %%

data = (
    users.loc[
        lambda x: (x.created_at.dt.year <= 2019) | (x.created_at.dt.month < 12)
    ]  # .loc[lambda x: x.created_at.dt.year >= 2019]
    # .assign(section=lambda x: x.section.fillna("Unknown"))
    .groupby(["section", pd.Grouper(key="created_at", freq="1m", label="right")])
    .size()
    .to_frame("count")
    .reset_index()
)

new_users_all = (
    alt.Chart(data)
    .mark_bar()
    .encode(
        y=alt.Y("count:Q", title="New users"),
        x=alt.X("year(created_at):T", title=None),
        color=alt.Color("section:N", scale=alt.Scale(scheme="category20b")),
        tooltip=["created_at", "section", "count"],
    )
)
# %%

data = (
    users.loc[
        lambda x: (x.created_at.dt.year.isin([2019, 2020]))
        & ((x.created_at.dt.year == 2019) | (x.created_at.dt.month < 12))
    ]
    # .assign(section=lambda x: x.section.fillna("Unknown"))
    .groupby(["section", pd.Grouper(key="created_at", freq="1m", label="right")])
    .size()
    .to_frame("count")
    .reset_index()
)

new_users_recent = (
    alt.Chart(data)
    .mark_bar()
    .encode(
        y=alt.Y("count:Q", title="New users"),
        x=alt.X("yearquarter(created_at):T", title=None),
        color=alt.Color("section:N", scale=alt.Scale(scheme="category20b")),
        tooltip=["created_at", "section", "count"],
    )
).properties(width=200)
# %%

# New users - small evidence of more adoption in Q2 2020; but only 10-15 businesses
export_chart(new_users_all | new_users_recent, "tweets_new_users")
new_users_all | new_users_recent
# %%
