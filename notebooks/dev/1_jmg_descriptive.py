# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     comment_magics: true
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.9.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Descriptive analysis

# %% [markdown]
# ## Preamble

# %%
# %run ../notebook_preamble.ipy

# %%
import altair as alt
import calendar
from toolz import pipe
from sg_covid_impact.descriptive import *
from sg_covid_impact.utils.altair_save_utils import *
from sg_covid_impact.make_sic_division import extract_sic_code_description

alt.data_transformers.disable_max_rows()

# %%
driver = google_chrome_driver_setup()

# %% [markdown]
# ## Collection and analysis

# %% [markdown]
# ### Some lookups

# %%
_SECTION_DIVISION_LOOKUP, _SECTION_NAME_LOOKUP = make_section_division_lookup()

_DIVISION_NAME_LOOKUP = extract_sic_code_description(load_sic_taxonomy(), "Division")

# %% [markdown]
# ### Claimant counts

# %%
cl = read_claimant_counts()
cl_norm = claimant_count_norm(cl)

# %%
plot_trend_point(cl_norm.query("nuts1=='Scotland'"), x_axis="month")

# %%
plot_claimant_trend_all_nuts(cl_norm)

# %% [markdown]
# ### Google search trends

# %%
d = read_search_trends()

# %%
trends_normalised = search_trend_norm(d)

# %%
plot_keyword_tends_chart(trends_normalised)

# %%
exposures_ranked = rank_sector_exposures(trends_normalised, "division")
exposures_ranked["division_name"] = exposures_ranked["division"].map(
    _DIVISION_NAME_LOOKUP
)
plot_ranked_exposures(exposures_ranked)

# %% [markdown]
# ### Share of employment in High exposure sectors

# %%
bres = read_official()

exposure_levels = exposures_ranked.merge(bres, left_on="division", right_on="division")

exposure_lad = make_exposure_shares(exposure_levels)

exposure_scot = (
    make_exposure_shares(exposure_levels, "nuts1")
    .query("nuts1=='Scotland'")
    .reset_index(drop=True)
)

# %%
plot_exposure_evol(exposure_scot)

# %%
exposure_scot_lads = make_exposure_shares(exposure_levels.query("nuts1 == 'Scotland'"))

plot_exposure_evol(exposure_scot_lads, mode="faceted", geo="geo_nm", columns=7)

# %% [markdown]
# ### Exposure national composition

# %%
exposure_levels_ = exposure_levels.copy()
exposure_levels_["is_scotland"] = [
    "Scotland" if x == "Scotland" else "Not Scotland" for x in exposure_levels["nuts1"]
]

# %%
exposure_levels_nat_comp = make_exposure_shares_detailed(
    exposure_levels_, "is_scotland"
)

# %%
plot_exposure_comparison(exposure_levels_nat_comp, month="interactive")

# %% [markdown]
# ### Evolution of exposure by LAD

# %%
high_exposure_scot = make_high_exposure(
    make_exposure_shares(exposure_levels.query("nuts1=='Scotland'"))
)

mean_high_exposure = (
    high_exposure_scot.query("month>3").groupby(["geo_nm"])["share"].mean().to_dict()
)
high_exposure_scot["mean_high_exposure"] = high_exposure_scot["geo_nm"].map(
    mean_high_exposure
)

# %%
exp_share_vars = {
    "geo_var": "geo_nm",
    "x_axis": "month",
    "y_axis": "share",
    "y_title": "Share high exposure",
    "color": "mean_high_exposure",
}

plot_trend_point(high_exposure_scot, **exp_share_vars).properties(width=300, height=200)

# %% [markdown]
# #### Composition of local economies and exposure to Covid 19

# %%
exposure_lad_detailed = make_exposure_shares_detailed(exposure_levels, "geo_nm")

# %%
plot_area_composition(
    exposure_lad_detailed, month=4, interactive=False, area="City of Edinburgh"
)

# %% [markdown]
# ### Maps

# %%
shapef = read_shape()

# %%
exposure_lad_codes = make_exposure_shares(exposure_levels, "geo_cd")

# %%
ms = [
    plot_time_choro(shapef, exposure_lad_codes, m, 8).properties(
        height=350, width=150, title=calendar.month_abbr[m]
    )
    for m in [4, 7, 10]
]

# %%
ms_series = (
    alt.hconcat(*ms).resolve_scale(color="independent").configure_view(strokeWidth=0)
)


ms_series

# %%
