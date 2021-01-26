# Script with functions from Scottish modelling

import os
import logging
import pandas as pd
import numpy as np
import sg_covid_impact
from sg_covid_impact.complexity import calc_eci
from sg_covid_impact.secondary_data import read_secondary
from sg_covid_impact.descriptive import (
    read_official,
    read_lad_nuts1_lookup,
    assign_nuts1_to_lad,
    calculate_sector_exposure,
    read_claimant_counts,
    claimant_count_norm,
    make_exposure_shares,
    make_high_exposure,
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


def make_div_share_variable(exposure_level=7, div_level=2):
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
    division_month_exposure_dict = exposures_ranked.set_index(["division", "month"])[
        "rank"
    ].to_dict()

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
    """Create a claimant count variable for modelling"""
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
    """Make secondary variables for modelling"""

    secondary = read_secondary()

    secondary_out = secondary.rename(columns={"geography_code": "geo_cd"})[
        ["geo_cd", "variable", "value"]
    ]

    return secondary_out


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
        .query("month>3")
        .pivot_table(index=["geo_cd", "month"], columns="variable", values="value")
    )

    # Present period exposure / diversification variables
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

    sec_vars = make_secondary_reg(keep, secondary)

    data = (
        X.merge(present, on=["geo_cd", "month"])
        .merge(lagged, on=["geo_cd", "month"])
        .merge(sec_vars, on="geo_cd")
    )

    return data


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
