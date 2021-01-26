# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     comment_magics: true
#     formats: notebooks///ipynb,notebooks///py:percent
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

# %%
# Modelling

# %run ../notebook_preamble.ipy

import logging
import pandas as pd
import numpy as np
import altair as alt
import sg_covid_impact
from sg_covid_impact.getters.nomis import get_BRES
from sg_covid_impact.complexity import *
from sg_covid_impact.secondary_data import read_secondary
from sg_covid_impact.descriptive import (
    read_official,
    read_lad_nuts1_lookup,
    assign_nuts1_to_lad,
    calculate_sector_exposure,
    read_claimant_counts,
    claimant_count_norm,
    read_search_trends,
    make_exposure_shares,
    search_trend_norm,
    make_high_exposure,
    rank_sector_exposures,
    make_exposure_shares_detailed,
)
from sg_covid_impact.make_sic_division import (
    extract_sic_code_description,
    load_sic_taxonomy,
)
from sg_covid_impact.diversification import (
    load_predicted,
    extract_sectors,
    extract_network,
    make_diversification_options,
    make_sector_space_base,
)
from sg_covid_impact.utils.altair_save_utils import *
import statsmodels.api as sm

project_dir = sg_covid_impact.project_dir


# %%
driver = google_chrome_driver_setup()


# %%
def make_exposure_share_variable(exposure_thres=7):

    logging.info("Calculating sector exposure")
    exposures_ranked = calculate_sector_exposure()[0]

    logging.info("Calculating local exposure shares")
    exposure_lad_codes = make_local_exposure_table(exposures_ranked)

    logging.info(f"Calculating high exposure shares level {exposure_thres}")
    exposure_high = (
        make_high_exposure(exposure_lad_codes, geo="geo_cd", level=exposure_thres)
        .assign(variable="exposure_share")
        .rename(columns={"share": "value"})
    )

    return exposure_high


# def make_sector_exposure_table():

#     d = read_search_trends()
#     trends_normalised = search_trend_norm(d)
#     exposures_ranked = rank_sector_exposures(trends_normalised,'division')

#     return exposures_ranked


def make_local_exposure_table(exposures_ranked):

    bres = read_official()
    exposure_levels = exposures_ranked.merge(
        bres, left_on="division", right_on="division"
    )
    exposure_lad_codes = make_exposure_shares(exposure_levels, "geo_cd")
    return exposure_lad_codes


def make_div_share_variable(exposure_level=7, div_level=2):

    _DIVISION_NAME_LOOKUP = extract_sic_code_description(
        load_sic_taxonomy(), "Division"
    )

    logging.info("Calculating sector exposure")
    exposures_ranked = calculate_sector_exposure()[0]
    division_month_exposure_dict = exposures_ranked.set_index(["division", "month"])[
        "rank"
    ].to_dict()

    logging.info("Making sector space")
    my_divisions = list(set(exposures_ranked["division"]))
    pr = load_predicted()
    pr_selected = pr[my_divisions]
    t = extract_sectors(pr_selected, 0.5)

    div_space = extract_network(t)
    p, g, l = make_sector_space_base(sector_space=div_space, extra_edges=70)

    logging.info("Calculating local exposure shares")
    bres = read_official()
    exposure_levels = exposures_ranked.merge(
        bres, left_on="division", right_on="division"
    )
    exposure_levels["division_name"] = exposure_levels["division"].map(
        _DIVISION_NAME_LOOKUP
    )
    exposure_shares_detailed = make_exposure_shares_detailed(
        exposure_levels, geo="geo_cd"
    )

    logging.info("Calculating diversification share rankings")
    monthly_diversification_rankings = pd.concat(
        [
            (
                make_diversification_options(
                    g,
                    division_month_exposure_dict,
                    m,
                    range(exposure_level, 10),
                    [0, 1, 2, 3],
                )
                .sort_values("mean", ascending=False)
                .assign(
                    divers_ranking=lambda x: pd.qcut(
                        x["mean"],
                        q=np.arange(0, 1.1, 0.25),
                        labels=False,
                        duplicates="drop",
                    )
                )
                .assign(month=m)
            )
            for m in range(3, 11)
        ]
    )

    # Merge with diversification information
    logging.info(f"Calculating diversification shares level {str(div_level)}")
    diversification_lad_detailed = exposure_levels.merge(
        monthly_diversification_rankings,
        left_on=["division", "month"],
        right_on=["division", "month"],
        how="outer",
    )

    diversification_lad_detailed["divers_ranking"] = diversification_lad_detailed[
        "divers_ranking"
    ].fillna("Less exposed")

    diversification_shares = (
        make_exposure_shares(
            diversification_lad_detailed, geography="geo_cd", variable="divers_ranking"
        )
        .query(f"divers_ranking == {div_level}")
        .assign(variable="low_diversification_share")
        .drop(axis=1, labels=["value"])
        .rename(columns={"share": "value"})[["month", "geo_cd", "variable", "value"]]
    ).reset_index(drop=True)

    return diversification_shares


def make_claimant_count_variable():
    """"""
    cl = read_claimant_counts()
    cl_count = (
        cl.query("measure_name=='Claimants as a proportion of residents aged 16-64'")[
            ["geography_code", "month", "obs_value"]
        ]
        .assign(variable="cl_count")
        .rename(columns={"obs_value": "value", "geography_code": "geo_cd"})
    )

    cl_norm_ = claimant_count_norm(cl)

    cl_norm = (
        cl_norm_[["geography_code", "month", "cl_norm"]]
        .rename(columns={"geography_code": "geo_cd", "cl_norm": "value"})
        .assign(variable="cl_count_norm")
    )

    return pd.concat([cl_count, cl_norm])


def make_secondary_variables():

    secondary = read_secondary()

    secondary_out = secondary.rename(columns={"geography_code": "geo_cd"})[
        ["geo_cd", "variable", "value"]
    ]

    return secondary_out


def make_lad_lookup(geo_var_name="LAD20"):

    meta_location = f"{project_dir}/data/raw/nspl/Documents"
    name_lu = pd.read_csv(
        os.path.join(meta_location, "LA_UA names and codes UK as at 04_20.csv")
    )
    name_dict = name_lu.set_index(f"{geo_var_name}CD")[f"{geo_var_name}NM"].to_dict()
    return name_dict


# %%
lad_name_code_lu = (
    pd.read_csv(
        "https://opendata.arcgis.com/datasets/c3ddcd23a15c4d7985d8b36f1344b1db_0.csv"
    )
    .set_index("LAD19CD")["LAD19NM"]
    .to_dict()
)

# %%
exp = make_exposure_share_variable()

# %%
div = make_div_share_variable()

# %%
cl = make_claimant_count_variable()

# %%
secondary = make_secondary_variables()

# %%
bres_sic_wide = get_BRES().pivot_table(index="geo_cd", columns="SIC4", values="value")

compl = (
    calc_eci(create_lq(bres_sic_wide, binary=True))
    .reset_index(drop=False)
    .assign(variable="eci")
    .rename(columns={"eci": "value"})
    .assign(value=lambda x: -x.value)
)
secondary = pd.concat([secondary, compl])

# %%
_SHORT_VAR_NAMES = {
    "% with NVQ4+ - aged 16-64": "% tertiary",
    "% with no qualifications (NVQ) - aged 16-64": "% no qual",
    "% with other qualifications (NVQ) - aged 16-64": "% other qual",
    "Annual pay - gross": "Gross annual pay",
    "Economic activity rate - aged 16-64": "Econ Activity rate",
    "Employment rate - aged 16-64": "Emp rate",
    "cl_count": "Claimant count",
    "cl_count_norm": "Claimant (normalised)",
    "smd_high_deprivation_share": "SMDI",
    "eci": "ECI",
}

sort_vars = [
    "Claimant count",
    "Claimant (normalised)",
    "ECI",
    "Emp rate",
    "Gross annual pay",
    "% tertiary",
    "% no qual",
]


# %%
### Visualise relationships between variables


def make_correlation_df(web_vars, other_vars):
    """Calculates correlations between exposure / diversification variables and secondary data"""
    out = []

    for w in web_vars:
        for o in other_vars:
            if "month" in o.columns:
                for v in set(o["variable"]):
                    for m in set(w["month"]):
                        my_w = w.query(f"month=={m}")
                        my_o = o.query(f"month=={m}").query(f"variable == '{v}'")
                        merg = my_w.merge(my_o, on="geo_cd")
                        my_v_name = list(set(w["variable"]))[0]
                        corr = np.float(merg[["value_x", "value_y"]].corr().iloc[0, 1])
                        res = pd.Series(
                            [my_v_name, v, m, corr],
                            index=["primary", "secondary", "month", "corr"],
                        )
                        out.append(res)
            else:
                for v in set(o["variable"]):
                    for m in set(w["month"]):
                        my_w = w.query(f"month=={m}")
                        my_o = o.query(f"variable == '{v}'")
                        merg = my_w.merge(my_o, on="geo_cd")
                        my_v_name = list(set(w["variable"]))[0]
                        corr = np.float(merg[["value_x", "value_y"]].corr().iloc[0, 1])
                        res = pd.Series(
                            [my_v_name, v, m, corr],
                            index=["primary", "secondary", "month", "corr"],
                        )
                        out.append(res)

    correlation_df = pd.DataFrame(out)

    correlation_df = correlation_df.assign(
        secondary_short=lambda x: x["secondary"].map(_SHORT_VAR_NAMES)
    )

    return correlation_df


# %%
web_vars = [div, exp]
other_vars = [cl, secondary]

correlation_df = make_correlation_df(web_vars, other_vars)
correlation_df = correlation_df.loc[
    ~correlation_df["secondary_short"].isin(
        ["% other qual", "SMDI", "Econ Activity rate"]
    )
]

# %%
ch = (
    alt.Chart(correlation_df.query("month>=3"))
    .mark_point(filled=True)
    .encode(
        x=alt.X("month", scale=alt.Scale(domain=[2.9, 10])),
        y="corr",
        facet=alt.Facet(
            "secondary_short",
            columns=2,
            sort=sort_vars,
            header=alt.Header(labelAngle=0, labelAnchor="start", labelOrient="top"),
        ),
        color="primary",
    )
).properties(width=300, height=50)

# %%
ch


# %%
def make_geo_average(ser):
    return ser.pivot_table(
        index="geo_cd", columns="variable", values="value", aggfunc="mean"
    )


# %%
all_vars_df_wide = pd.concat(
    [make_geo_average(x) for x in [div, exp, cl, secondary]], axis=1
)

all_vars_df_corr = all_vars_df_wide.corr()

exp_div_corr = (
    all_vars_df_corr[["low_diversification_share", "exposure_share"]]
    .drop(
        index=[
            "cl_count",
            "cl_count_norm",
            "low_diversification_share",
            "exposure_share",
            "smd_high_deprivation_share",
            "% with other qualifications (NVQ) - aged 16-64",
        ]
    )
    .reset_index(drop=False)
    .melt(id_vars="variable", var_name="exposure_measure")
)
exp_div_corr["v"] = 0

base = alt.Chart(exp_div_corr).properties(width=150, height=200)


out = base.mark_point(filled=True, size=75, stroke="black", strokeWidth=0.5).encode(
    y=alt.Y(
        "variable",
        title="Variable",
        sort=alt.EncodingSortField("value", op="min", order="descending"),
    ),
    x="value",
    color=alt.Color(
        "exposure_measure",
        # scale=alt.Scale(scheme='spectral'))
    ),
)
out_lines = base.mark_line(stroke="grey", strokeWidth=1, strokeDash=[2, 1]).encode(
    y=alt.Y(
        "variable",
        title="Variable",
        sort=alt.EncodingSortField("value", op="min", order="descending"),
    ),
    x="value",
    # color='exposure_measure',
    detail="variable",
)

vline = base.mark_rule().encode(x=alt.X("v", title="Correlation coefficient"))

ch = out + out_lines + vline

ch

# %%
_LAD_NUTS_LU = read_lad_nuts1_lookup()

exp_wide = (
    pd.concat([make_geo_average(x) for x in [div, exp]], axis=1)
    .reset_index(drop=False)
    .assign(nuts1=lambda x: x["geo_cd"].apply(assign_nuts1_to_lad))
    .melt(id_vars=["geo_cd", "nuts1"])
)

sorted_nuts = (
    exp_wide.query("variable=='low_diversification_share'")
    .groupby("nuts1")["value"]
    .mean()
    .sort_values(ascending=False)
    .index.tolist()
)

bp = (
    alt.Chart(exp_wide)
    .mark_boxplot()
    .encode(
        x="value",
        y=alt.Y("nuts1", sort=sorted_nuts),
        column="variable",
        color=alt.Color("variable", legend=None),
    )
).properties(height=200, width=150)
bp

# %%
geo_diffs = alt.vconcat(bp, ch).resolve_scale(color="independent")
save_altair(geo_diffs, "geo_comparisons", driver)

geo_diffs


# %% [markdown]
# ### Run regression

# %%
def make_lagged_web(var, name):

    results = []

    var_ = var.query("month>=3")

    for m in set(var_["month"]):
        pre = var_.query(f"month<{m}")
        stat = pre.groupby(["geo_cd", "variable"])["value"].mean()
        stat.name = m
        # stat.assign(month=m)
        results.append(stat)

    lagged = (
        pd.concat(results, axis=1)
        .loc[:, range(4, 11)]
        .reset_index(drop=False)
        .melt(id_vars=["geo_cd", "variable"], var_name="month")
        .drop(axis=1, labels=["variable"])
        .rename(columns={"value": f"{name}_lagged"})
        .set_index(["geo_cd", "month"])
    )
    return lagged


def make_secondary_reg(keep):

    sec_wide = make_geo_average(secondary)
    sec_wide.columns = [_SHORT_VAR_NAMES[x] for x in sec_wide.columns]

    return sec_wide[keep]


# %%

# %%
_SEC_KEEP = ["% tertiary", "% no qual", "Gross annual pay", "Emp rate", "ECI"]


# %%
def make_regression_table(
    secondary, keep=["% tertiary", "Gross annual pay", "Emp rate", "ECI", "% no qual"]
):

    X = (
        cl.copy()
        .query("month>3")
        .pivot_table(index=["geo_cd", "month"], columns="variable", values="value")
    )

    # Present period
    present = pd.concat(
        [
            var.rename(columns={"value": f"{name}_present"})
            .query("month>3")
            .set_index(["month", "geo_cd"])
            .drop(axis=1, labels=["variable"])
            for var, name in zip([exp, div], ["exposure_share", "low_div_share"])
        ],
        axis=1,
    ).reset_index(drop=False)

    lagged = pd.concat(
        [
            make_lagged_web(v, name)
            for v, name in zip([exp, div], ["exposure_share", "low_div_share"])
        ],
        axis=1,
    ).reset_index(drop=False)

    sec_vars = make_secondary_reg(keep)

    data = (
        X.merge(present, on=["geo_cd", "month"])
        .merge(lagged, on=["geo_cd", "month"])
        .merge(sec_vars, on="geo_cd")
    )
    # data = pd.concat([data,pd.get_dummies(data['geo_cd'])],axis=1)

    return data


# %%
reg_table = make_regression_table(secondary)


# %%
def fit_regression(table, dep, indep_focus, fe=True):

    table_ = table.dropna(axis=0)

    Y = table_[dep]

    indep = table_[[x for x in table_.columns if indep_focus in x]]

    other_vars = table_.drop(
        columns=[
            "cl_count",
            "cl_count_norm",
            "exposure_share_present",
            "exposure_share_lagged",
            "low_div_share_present",
            "low_div_share_lagged",
            "geo_cd",
        ]
    )

    fe = pd.get_dummies(table_["geo_cd"])

    exog = pd.concat([indep, other_vars, fe], axis=1)

    # exog=sm.add_constant(exog)
    lm = sm.OLS(endog=Y, exog=exog)
    return lm.fit(cov_type="HC2")
    # return exog


def extract_model_results(model, name):
    """Model"""
    res = pd.concat([model.params, model.conf_int()], axis=1)
    res.columns = ["coefficient", "min", "max"]
    res["indep"] = "_".join(name.split("_")[:-1])

    return res


# %%
# out = fit_regression(reg_table,'cl_count','exp')

mods = {}

for dep in ["cl_count", "cl_count_norm"]:
    for indep in ["exp", "div"]:
        mods[f"{dep}_{indep}"] = fit_regression(reg_table, dep, indep)

model_results = pd.concat([extract_model_results(v, name=k) for k, v in mods.items()])

my_vars = [
    "exposure_share_present",
    "exposure_share_lagged",
    "low_div_share_present",
    "low_div_share_lagged",
]

# %%
model_selected = (
    model_results.reset_index(drop=False).loc[model_results.index.isin(my_vars)]
).reset_index(drop=True)

model_selected["pred"] = [
    "exp share" if "exposure" in x else "low div share" for x in model_selected["index"]
]
model_selected["temporal"] = [
    "lagged" if "lagged" in x else "present" for x in model_selected["index"]
]

# %%
base = alt.Chart().encode(y=alt.Y("temporal", sort=["present", "lagged"], title=None))


ch = (
    base.mark_bar().encode(x="coefficient", color=alt.Color("temporal", legend=None))
).properties(width=120, height=75)
err = (
    base.mark_errorbar(color="black").encode(
        x=alt.X("min", title="Coefficient"), x2="max"
    )
).properties(width=120, height=75)

reg_plot = alt.layer(ch, err, data=model_selected).facet(
    column=alt.Column("indep", title=None),
    row=alt.Row("pred", sort=["exp", "diversification"], title="Measure of exposure"),
)

save_altair(reg_plot, "coeff_plot", driver)

reg_plot


# %% [markdown]
# ### Bivariate correlations

# %%
def make_tidy_agg_table(exp_vars, out_vars, secondary_vars):
    # Here we correlate our vars (exposure and diversification) with secondary

    scatter_table = reg_table.copy()
    scatter_table["nuts1"] = scatter_table["geo_cd"].apply(assign_nuts1_to_lad)
    scatter_table["is_scotland"] = scatter_table["nuts1"] == "Scotland"
    scatter_table["geo_nm"] = scatter_table["geo_cd"].map(lad_name_code_lu)

    tidy_agg_table = [
        (
            scatter_table.groupby("geo_cd")[sel_vars]
            .mean()
            .reset_index(drop=False)
            .melt(
                id_vars=["geo_cd"],
                var_name=var_name + "_var",
                value_name=var_name + "_value",
            )
            .set_index("geo_cd")
        )
        for sel_vars, var_name in zip(
            [exp_vars, out_vars, secondary_vars], ["exposure", "claimant", "secondary"]
        )
    ]
    tidy_agg_df = (
        pd.merge(tidy_agg_table[0], tidy_agg_table[1], on="geo_cd")
        .merge(tidy_agg_table[2], on="geo_cd")
        .reset_index(drop=False)
        .assign(nuts1=lambda x: x["geo_cd"].apply(assign_nuts1_to_lad))
        .assign(is_scotland=lambda x: x["nuts1"] == "Scotland")
        .assign(geo_nm=lambda x: x["geo_cd"].map(lad_name_code_lu))
        .query("geo_nm !='Isles of Scilly'")
        .query("nuts1=='Scotland'")
    )
    return tidy_agg_df


# %%
# Here we correlate our vars (exposure and diversification) with secondary

exp_vars = ["exposure_share_present", "low_div_share_present"]
out_vars = ["cl_count_norm"]
secondary_vars = _SEC_KEEP

tidy_agg_df = make_tidy_agg_table(exp_vars, out_vars, secondary_vars)

# %%
base_scatter = alt.Chart(tidy_agg_df).encode(
    x=alt.X("exposure_value", scale=alt.Scale(zero=False), axis=alt.Axis(title=None)),
    y=alt.Y("secondary_value", scale=alt.Scale(zero=False), axis=alt.Axis(title=None)),
)

base_point = base_scatter.mark_point(
    filled=True, stroke="black", strokeWidth=0.2
).encode(
    color=alt.Color(
        "claimant_value:Q", scale=alt.Scale(scheme="Spectral"), sort="descending"
    ),
    tooltip=["geo_nm"],
)


base_reg = base_scatter.transform_regression(
    "exposure_value", "secondary_value"
).mark_line(strokeWidth=2, strokeDash=[2, 1])

params = (
    base_scatter.transform_regression("exposure_value", "secondary_value", params=True)
    .mark_text(align="left", color="red")
    .encode(x=alt.value(150), y=alt.value(20), text=alt.Text("rSquared:N", format=".3"))
)

regressions = (
    (base_point + base_reg + params)
    .properties(width=200, height=100)
    .facet(row="secondary_var", column="exposure_var")
    .resolve_scale(y="independent", x="independent")
)

save_altair(regressions, "scatter_plots", driver=driver)

regressions

# %% [markdown]
# #### Correlate div share and claimant counts normalised

# %%
my_vars = ["cl_count", "cl_count_norm", "exposure_share_lagged", "low_div_share_lagged"]

reg_table_ = reg_table.copy()
reg_table_["nuts1"] = reg_table_["geo_cd"].apply(assign_nuts1_to_lad)
reg_table_["is_scotland"] = [
    "Scotland" if x == "Scotland" else "Not Scotland" for x in reg_table_["nuts1"]
]

reg_results = (
    reg_table_.groupby(["month", "is_scotland"])
    .apply(lambda x: x[my_vars].corr())
    .reset_index(drop=False)[
        [
            "month",
            "is_scotland",
            "level_2",
            "exposure_share_lagged",
            "low_div_share_lagged",
        ]
    ]
)
reg_results = (
    reg_results.loc[reg_results["level_2"].isin(["cl_count", "cl_count_norm"])]
    .melt(id_vars=["month", "level_2", "is_scotland"])
    .reset_index(drop=False)
)

reg_results["x"] = 0

reg_results

corr_ch = (
    alt.Chart(reg_results)
    .mark_point(filled=True)
    .encode(x="month", y=alt.Y("value", title="Correlation"), color="variable")
    .properties(height=100, width=120)
)

corr_line = (
    alt.Chart(reg_results).mark_rule(strokeDash=[3, 1], stroke="black").encode(y="x")
).properties(height=100, width=120)

corr_evol = (corr_ch + corr_line).facet(
    column=alt.Column("level_2", title="Claimant variable"),
    row=alt.Row("is_scotland", title=None),
)

regression_results = alt.vconcat(corr_evol, reg_plot).resolve_scale(color="independent")


save_altair(regression_results, "regression_results", driver=driver)

regression_results

# %%
exp_vars_2 = ["exposure_share_lagged", "low_div_share_lagged"]
out_vars = ["cl_count_norm"]
secondary_vars = _SEC_KEEP

tidy_agg_df_2 = make_tidy_agg_table(exp_vars_2, out_vars, secondary_vars)

# %%
exposure_claimant = (
    tidy_agg_df_2.drop_duplicates(
        ["geo_cd", "exposure_var", "claimant_var"]
    ).reset_index(drop=True)
)[["geo_cd", "exposure_var", "exposure_value", "claimant_var", "claimant_value"]]

exposure_average_ranking = (
    exposure_claimant.groupby(["exposure_var"])
    .apply(
        lambda x: x.assign(
            exposure_rank=lambda df: pd.qcut(
                df["exposure_value"], q=np.arange(0, 1.1, 0.25), labels=False
            )
        )
    )
    .reset_index(drop=True)[["geo_cd", "exposure_var", "exposure_rank"]]
)

exposure_claimant = exposure_claimant.merge(
    exposure_average_ranking, on=["geo_cd", "exposure_var"]
)

exposure_claimant.groupby(["exposure_var", "exposure_rank"])["claimant_value"].mean()

# %%
lad_name_lu = make_lad_lookup()

# %%
set(secondary["variable"])

# %%
low_div = div.query("month==10")[["geo_cd", "value"]].rename(
    columns={"value": "div_share"}
)
cl_norm = (
    cl.query("variable=='cl_count_norm'")
    .groupby("geo_cd")["value"]
    .mean()
    .reset_index(name="claim_mean")
)
sec = secondary.pivot_table(index="geo_cd", columns="variable", values="value")[
    [
        "smd_high_deprivation_share",
        "Annual pay - gross",
        "% with no qualifications (NVQ) - aged 16-64",
        "% with NVQ4+ - aged 16-64",
        "Employment rate - aged 16-64",
    ]
]

combi = (
    low_div.merge(cl_norm, on="geo_cd")
    .merge(sec, on="geo_cd")
    .assign(nuts1=lambda x: x["geo_cd"].apply(assign_nuts1_to_lad))
    .assign(lad_name=lambda x: x["geo_cd"].map(lad_name_lu))
    .query("nuts1=='Scotland'")
)


# %%

# %%
example_chart = (
    alt.Chart(combi)
    .mark_point(filled=True, stroke="black", strokeWidth=0.5)
    .encode(
        x=alt.X(
            "div_share",
            scale=alt.Scale(zero=False),
            title=[
                "Employment in sectors with low diversification options",
                "(October)",
            ],
        ),
        y=alt.Y(
            "claim_mean",
            scale=alt.Scale(zero=False, domain=[1, 2.5]),
            title="Normalised claimant counts (average)",
        ),
        size="smd_high_deprivation_share",
        color=alt.Color(
            "Annual pay - gross",
            sort="descending",
            scale=alt.Scale(scheme="Spectral", type="quantile"),
        ),
        tooltip=["lad_name"],
    )
)
save_altair(example_chart, "example_chart", driver)

example_chart


# %%
