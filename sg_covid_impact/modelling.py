# Functions from Scottish modelling

import os
import logging
import datetime
import pandas as pd
import numpy as np
import altair as alt
import sg_covid_impact
from sg_covid_impact.getters.nomis import get_BRES
from sg_covid_impact.complexity import calc_eci, create_lq
from sg_covid_impact.secondary_data import read_secondary
from sg_covid_impact.descriptive import (
    read_official,
    assign_nuts1_to_lad,
    calculate_sector_exposure,
    read_claimant_counts,
    claimant_count_norm,
    make_exposure_shares,
    make_high_exposure,
)
from sg_covid_impact.make_sic_division import (
    extract_sic_code_description,
    load_sic_taxonomy,
)
from sg_covid_impact.diversification import (
    month_string_from_datetime,
    make_month_range,
    load_predicted,
    extract_sectors,
    extract_network,
    make_diversification_options,
    make_sector_space_base,
)


import statsmodels.api as sm

project_dir = sg_covid_impact.project_dir


def make_lad_lookup(geo_var_name="LAD20"):
    """Make LAD code - name lookup
    Args:
        geo_var_name: Name of the geo name variable in the NSPL documentation
    """

    meta_location = f"{project_dir}/data/raw/nspl/Documents"
    name_lu = pd.read_csv(
        os.path.join(meta_location, "LA_UA names and codes UK as at 04_20.csv")
    )
    name_dict = name_lu.set_index(f"{geo_var_name}CD")[f"{geo_var_name}NM"].to_dict()
    return name_dict


def make_local_exposure_table(exposures_ranked):
    """Creates a table of LAD employment exposure shares in all sectors
    Args:
        exposure_ranked (df) are the exposure ranks by sector and month
    """

    bres = read_official()
    exposure_levels = exposures_ranked.merge(
        bres, left_on="division", right_on="division"
    )
    exposure_lad_codes = make_exposure_shares(exposure_levels, "geo_cd")
    return exposure_lad_codes


def make_exposure_share_variable(exposure_thres=7):
    """Extracts exposure shares by LAD
    Args:
        exposure_thres (int): exposure ranking
    """
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


def make_div_share_variable(exposure_level=7, div_level=3):
    """Calculates the share of employment in a low diversification sector
    Args:
        exposure_level (int): min threshold for high exposure
        div_leve (int): min threshold for low diversification
    """

    _DIVISION_NAME_LOOKUP = extract_sic_code_description(
        load_sic_taxonomy(), "Division"
    )

    logging.info("Calculating sector exposure")
    exposures_ranked = calculate_sector_exposure()[0]

    my_divisions = list(set(exposures_ranked["division"]))

    division_month_exposure_dict = (
        exposures_ranked
        # Here we need to turn the timestamps into strings for merging
        .assign(month_str=lambda x: x["month_year"].apply(month_string_from_datetime))
        .set_index(["division", "month_str"])["rank"]
        .to_dict()
    )

    logging.info("Making sector space")
    my_divisions = list(set(exposures_ranked["division"]))
    pr = load_predicted()
    pr_selected = pr[my_divisions]
    t = extract_sectors(pr_selected, 0.5)

    div_space = extract_network(t)
    p, g, lnk = make_sector_space_base(sector_space=div_space, extra_edges=70)

    logging.info("Calculating local exposure shares")
    bres = read_official()

    exposure_levels = exposures_ranked.merge(
        bres, left_on="division", right_on="division"
    )
    exposure_levels["division_name"] = exposure_levels["division"].map(
        _DIVISION_NAME_LOOKUP
    )
    # exposure_lad_detailed = make_exposure_shares_detailed(exposure_levels, "geo_nm")

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
                .assign(month_year=m)
            )
            for m in make_month_range("2020-03-01", "2021-02-01")
        ]
    )

    # Merge with diversification information
    logging.info(f"Calculating diversification shares level {str(div_level)}")
    diversification_lad_detailed = exposure_levels.assign(
        month_year=lambda x: x["month_year"].apply(month_string_from_datetime)
    ).merge(
        monthly_diversification_rankings,
        left_on=["division", "month_year"],
        right_on=["division", "month_year"],
        how="outer",
    )
    diversification_lad_detailed["divers_ranking"] = diversification_lad_detailed[
        "divers_ranking"
    ].fillna("Less exposed")

    diversification_shares = (
        make_exposure_shares(
            diversification_lad_detailed, geography="geo_cd", variable="divers_ranking"
        )
        .query("divers_ranking!='Less exposed'")
        .query(f"divers_ranking >= {div_level}")
        .groupby(["geo_cd", "month_year"])["share"]
        .sum()
        .reset_index(name="share")
        .assign(variable="low_diversification_share")
        .rename(columns={"share": "value"})[
            ["month_year", "geo_cd", "variable", "value"]
        ]
        .assign(month_year=lambda x: pd.to_datetime(x["month_year"]))
        .reset_index(drop=True)
    )

    return diversification_shares


def make_claimant_count_variable():
    """Create a claimant count variable for modelling"""
    cl = read_claimant_counts()
    cl_count = (
        cl.query("measure_name=='Claimants as a proportion of residents aged 16-64'")[
            ["geography_code", "date", "obs_value"]
        ]
        .assign(variable="cl_count")
        .rename(columns={"obs_value": "value", "geography_code": "geo_cd"})
    )

    cl_norm_ = claimant_count_norm(cl)

    cl_norm = (
        cl_norm_[["geography_code", "date", "cl_norm"]]
        .rename(columns={"geography_code": "geo_cd", "cl_norm": "value"})
        .assign(variable="cl_count_norm")
    )

    return pd.concat([cl_count, cl_norm])


def make_secondary_variables():
    """Make secondary variables for modelling"""

    secondary = read_secondary()

    secondary_out = secondary.rename(columns={"geography_code": "geo_cd"})[
        ["geo_cd", "variable", "value"]
    ]
    compl = make_complexity()

    return pd.concat([secondary_out, compl])


def make_complexity():
    """Make complexity variable"""
    bres_sic_wide = get_BRES().pivot_table(
        index="geo_cd", columns="SIC4", values="value"
    )

    compl = (
        calc_eci(create_lq(bres_sic_wide, binary=True))
        .reset_index(drop=False)
        .assign(variable="eci")
        .rename(columns={"eci": "value"})
        .assign(value=lambda x: -x.value)
    )
    return compl


def make_geo_average(ser):
    """Returns averages for a variable (eg over multiple months) in a location"""
    return ser.pivot_table(
        index="geo_cd", columns="variable", values="value", aggfunc="mean"
    )


# TODO - will need to fix these functions to deal with newer data
def make_lagged_web(var, name):
    """Takes a variable and returns the lagged values (ie mean of
    values before its current month)
    """

    results = []

    var_ = var.query("month_year>'2020-03-01'")

    for m in set(var_["month_year"]):
        pre = var_.query(f"month_year<'{m}'")
        stat = pre.groupby(["geo_cd", "variable"])["value"].mean()
        stat.name = m
        # stat.assign(month=m)
        results.append(stat)

    results_df = pd.concat(results, axis=1)
    lagged = (
        results_df.loc[
            :, [x > datetime.datetime(2020, 4, 1) for x in results_df.columns]
        ]
        .reset_index(drop=False)
        .melt(id_vars=["geo_cd", "variable"], var_name="month_year")
        .drop(axis=1, labels=["variable"])
        .rename(columns={"value": f"{name}_lagged"})
        .set_index(["geo_cd", "month_year"])
    )
    return lagged


def make_secondary_reg(keep, secondary):
    """Make secondary data for the regression
    Args:
        keep (list): variables to leep
        secondary (df): df with secondary data
    """
    sec_wide = make_geo_average(secondary)
    sec_wide.columns = [_SHORT_VAR_NAMES[x] for x in sec_wide.columns]

    return sec_wide[keep]


def make_regression_table(
    cl,
    exp,
    div,
    secondary,
    keep=["% tertiary", "Gross annual pay", "Emp rate", "ECI", "% no qual"],
):
    """Creates a table with all the data we need for the regression
    Args:
        cl (df): claimant counts ie the outcome variable
        exp (df): measures of exposure
        div (df): measures of diversification
        secondary (df): secondary variables
    """
    # pivots over variables
    X = (
        cl.copy()
        .query("date>'2020-03-01'")
        .rename(columns={"date": "month_year"})
        .pivot_table(index=["geo_cd", "month_year"], columns="variable", values="value")
    )

    # Present period exposure / diversification variables
    present = pd.concat(
        [
            var.rename(columns={"value": f"{name}_present"})
            .query("month_year>'2020-03-01'")
            .set_index(["month_year", "geo_cd"])
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

    sec_vars = make_secondary_reg(keep, secondary)

    data = (
        X.merge(present, on=["geo_cd", "month_year"])
        .merge(lagged, on=["geo_cd", "month_year"])
        .merge(sec_vars, on="geo_cd")
    )

    return data


def make_tidy_agg_table(
    reg_table, exp_vars, out_vars, secondary_vars, nuts_focus="Scotland"
):
    """Correlate our vars (exposure and diversification) with secondary
    Args:
        reg_table
        exp_vars (list): variables that capture exposure
        out_vars (list): variables that capture outputs
        secondary_vars (list): secondary variables
    """

    # Create scatter table
    scatter_table = (
        reg_table.copy()
        .assign(nuts1=lambda x: x["geo_cd"].apply(assign_nuts1_to_lad))
        .assign(is_focus=lambda x: x["nuts1"] == nuts_focus)
        .assign(geo_nm=lambda x: x["geo_cd"].map(lad_name_code_lu))
        .rename(columns={"is_focus": f"is_{nuts_focus}"})
    )

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
        .assign(is_scotland=lambda x: x["nuts1"] == nuts_focus)
        .assign(geo_nm=lambda x: x["geo_cd"].map(lad_name_code_lu))
        .query("geo_nm !='Isles of Scilly'")
        .query(f"nuts1=='{nuts_focus}'")
    )
    return tidy_agg_df


def plot_variable_correlations(tidy_agg_df):
    """Plots bivariate correlations between variables of interest"""
    base_scatter = alt.Chart(tidy_agg_df).encode(
        x=alt.X(
            "exposure_value", scale=alt.Scale(zero=False), axis=alt.Axis(title=None)
        ),
        y=alt.Y(
            "secondary_value", scale=alt.Scale(zero=False), axis=alt.Axis(title=None)
        ),
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
        base_scatter.transform_regression(
            "exposure_value", "secondary_value", params=True
        )
        .mark_text(align="left", color="red")
        .encode(
            x=alt.value(150), y=alt.value(20), text=alt.Text("rSquared:N", format=".3")
        )
    )

    scatters = (
        (base_point + base_reg + params)
        .properties(width=200, height=100)
        .facet(row="secondary_var", column="exposure_var")
        .resolve_scale(y="independent", x="independent")
    )

    return scatters


def plot_correlation_evolution(reg_table, nuts_focus="Scotland"):
    """Plots evolution of correlation between variables"""
    my_vars = [
        "cl_count",
        "cl_count_norm",
        "exposure_share_lagged",
        "low_div_share_lagged",
    ]

    # Calculates correlations between variables over months
    reg_table_ = reg_table.copy()
    reg_table_["nuts1"] = reg_table_["geo_cd"].apply(assign_nuts1_to_lad)
    reg_table_[f"is_{nuts_focus}"] = [
        nuts_focus if x == nuts_focus else f"Not {nuts_focus}"
        for x in reg_table_["nuts1"]
    ]

    reg_results = (
        reg_table_.groupby(["month_year", f"is_{nuts_focus}"])
        .apply(lambda x: x[my_vars].corr())
        .reset_index(drop=False)[
            [
                "month_year",
                f"is_{nuts_focus}",
                "level_2",
                "exposure_share_lagged",
                "low_div_share_lagged",
            ]
        ]
    )
    reg_results = (
        reg_results.loc[reg_results["level_2"].isin(["cl_count", "cl_count_norm"])]
        .melt(id_vars=["month_year", "level_2", f"is_{nuts_focus}"])
        .reset_index(drop=False)
    )

    reg_results["x"] = 0

    corr_ch = (
        alt.Chart(reg_results)
        .mark_point(filled=True)
        .encode(
            x=alt.X("yearmonth(month_year):O", title=None),
            y=alt.Y("value", title="Correlation"),
            color="variable",
        )
        .properties(height=100, width=120)
    )

    corr_line = (
        alt.Chart(reg_results)
        .mark_rule(strokeDash=[3, 1], stroke="black")
        .encode(y="x")
    ).properties(height=100, width=120)

    corr_evol = (corr_ch + corr_line).facet(
        column=alt.Column("level_2", title="Claimant variable"),
        row=alt.Row(f"is_{nuts_focus}", title=None),
    )

    return corr_evol


def fit_regression(table, dep, indep_focus, fe=True):
    """Fits regression
    Args:
        table (df): table with all the variables we will use in the regression
        dep (str): dependent variable
        indep_focus: independent variables we focus on
        fe (bool): if we include place fixed effects
    """

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
            "month_year",
        ]
    )

    fe = pd.get_dummies(table_["geo_cd"])

    exog = pd.concat([indep, other_vars, fe], axis=1)

    # exog=sm.add_constant(exog)
    lm = sm.OLS(endog=Y, exog=exog)
    return lm.fit(cov_type="HC2")
    # return exog


def extract_model_results(model, name):
    """Extract models results for plotting
    Args:
        model (statmodels model): model object with results
        name (str): name of the model
    """
    res = pd.concat([model.params, model.conf_int()], axis=1)
    res.columns = ["coefficient", "min", "max"]
    res["indep"] = "_".join(name.split("_")[:-1])

    return res


# def plot_variable_correlations(exp, div, cl, secondary):
#     """Plots correlations between variables in our model
#     Args:
#         exp (df): share of emp in high exposure sectors
#         div (df): share of emp in low diversification sectors
#         cl (df): claimant counts
#         secondary (df): secondary variables
#     """
#     all_vars_df_wide = pd.concat(
#         [make_geo_average(x) for x in [div, exp, cl, secondary]], axis=1
#     )

#     all_vars_df_corr = all_vars_df_wide.corr()

#     # Calculate correlations
#     exp_div_corr = (
#         all_vars_df_corr[["low_diversification_share", "exposure_share"]]
#         .drop(
#             index=[
#                 "cl_count",
#                 "cl_count_norm",
#                 "low_diversification_share",
#                 "exposure_share",
#                 "smd_high_deprivation_share",
#                 "% with other qualifications (NVQ) - aged 16-64",
#             ]
#         )
#         .reset_index(drop=False)
#         .melt(id_vars="variable", var_name="exposure_measure")
#     )
#     exp_div_corr["v"] = 0

#     base = (
#         alt.Chart(exp_div_corr).encode(
#             y=alt.Y(
#                 "variable",
#                 title="Variable",
#                 sort=alt.EncodingSortField("value", op="min", order="descending"),
#             ),
#             x="value",
#         )
#     ).properties(width=150, height=200)

#     # Point plot
#     out = base.mark_point(filled=True, size=75, stroke="black", strokeWidth=0.5).encode(
#         color=alt.Color("exposure_measure")
#     )
#     out_lines = base.mark_line(stroke="grey", strokeWidth=1, strokeDash=[2, 1]).encode(
#         detail="variable"
#     )

#     vline = base.mark_rule().encode(x=alt.X("v", title="Correlation coefficient"))

#     ch = out + out_lines + vline

#     return ch


def plot_model_coefficients(model_selected):
    """Plots model coefficients"""
    base = alt.Chart().encode(
        y=alt.Y("temporal", sort=["present", "lagged"], title=None)
    )

    ch = (
        base.mark_bar().encode(
            x="coefficient", color=alt.Color("temporal", legend=None)
        )
    ).properties(width=400, height=150)
    err = (
        base.mark_errorbar(color="black").encode(
            x=alt.X("min", title="Coefficient"), x2="max"
        )
    ).properties(width=400, height=150)

    reg_plot = alt.layer(ch, err, data=model_selected).facet(
        column=alt.Column("indep", title=None),
        row=alt.Row(
            "pred", sort=["exp", "diversification"], title="Measure of exposure"
        ),
    )

    return reg_plot


lad_name_code_lu = make_lad_lookup()

_SHORT_VAR_NAMES = {
    "% with NVQ4+ - aged 16-64": "% tertiary",
    "% with no qualifications (NVQ) - aged 16-64": "% no qual",
    "% with other qualifications (NVQ) - aged 16-64": "% other qual",
    "Annual pay - gross": "Gross annual pay",
    "Economic activity rate - aged 16-64": "Economic Activity rate",
    "Employment rate - aged 16-64": "Emp rate",
    "cl_count": "Claimant count rate",
    "cl_count_norm": "Claimant count rate (normalised)",
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

clean_var_name = {
    "% no qual": "% no qualification",
    "% tertiary": "% tertiary",
    "ECI": "Economic Complexity Index",
    "Emp rate": "Employment rate",
    "Gross annual pay": "Gross Annual Pay",
    "cl_count": "Claimant count rate",
    "cl_count_norm": "Claimant count rate (normalised)",
    "exposure_share_lagged": "Exp employment share (lagged)",
    "exposure_share_present": "Exp employment share (present)",
    "low_div_share_lagged": "Low div. employment share (lagged)",
    "low_div_share_present": "Low div employment share (present)",
}

order_vars = [
    "Claimant count rate",
    "Claimant count rate (normalised)",
    "Employment rate",
    "Gross Annual Pay",
    "% no qualification",
    "% tertiary",
    "Economic Complexity Index",
    "Exp employment share (present)",
    "Exp employment share (lagged)",
    "Low div employment share (present)",
    "Low div. employment share (lagged)",
]


def make_correlation_plot(reg_table):
    
    # Create correlation table
    corr_plot = (reg_table.iloc[:,2:].corr()
                 .reset_index(drop=False)
                 .melt(id_vars='index',var_name='variable_2')
                 .reset_index(drop=True)
                 .rename(columns={'index':'variable_1',0:'v2'}))
    
    # Clean variable names
    for v in ['variable_1','variable_2']:
        corr_plot[v] = corr_plot[v].map(clean_var_name)
    
    # Absolute value for circle sizes
    corr_plot['size']= np.abs(corr_plot['value'])

    # Avoid dominance by diagonal
    for rid,r in corr_plot.iterrows():
        if r['variable_1']==r['variable_2']:
            corr_plot.loc[rid,'value']=0
    
    # Round coefficient for tooltip
    corr_plot['coeff'] = [str(np.round(x,3))if x!=0 else '' for
                          x in corr_plot['value']]
    
    ch = (alt.Chart(corr_plot)
      .mark_rect()
      .encode(x=alt.X('variable_1',title=None,sort=order_vars,
                     axis=alt.Axis(labelAngle=315)),
              y=alt.Y('variable_2',title=None,sort=order_vars),
              tooltip=['variable_1','variable_2','coeff'],
              color=alt.Color('value:Q',sort='descending',title='Correlation',
                              scale=alt.Scale(scheme='Spectral'))))

    text = (alt.Chart(corr_plot)
          .mark_text()
          .encode(x=alt.X('variable_1',title=None,sort=order_vars,
                         axis=alt.Axis(labelAngle=315)),
                  y=alt.Y('variable_2',title=None,sort=order_vars),
                  text='coeff',
                  opacity=alt.Opacity('size',legend=None,
                                      scale=alt.Scale(range=[0.3,1]))))

    return (ch+text).properties(width=500)
