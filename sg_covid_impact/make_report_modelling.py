# Models relations between variables of interest
import yaml
import altair as alt
import pandas as pd
from sg_covid_impact.utils.altair_save_utils import (
    google_chrome_driver_setup,
    save_altair,
)
from sg_covid_impact.modelling import (
    make_div_share_variable,
    make_claimant_count_variable,
    make_secondary_variables,
    make_exposure_share_variable,
    plot_variable_correlations,
    make_regression_table,
    fit_regression,
    extract_model_results,
    plot_model_coefficients,
    make_tidy_agg_table,
    plot_correlation_evolution,
    make_correlation_plot,
    make_predicted_values,
    plot_predictions,
    combine_predicted_actual,
)

import sg_covid_impact


#######
# Preamble
#######

project_dir = sg_covid_impact.project_dir

alt.data_transformers.disable_max_rows()
driver = google_chrome_driver_setup()

FIG_PATH = f"{project_dir}/figures/scotland"
# make_fig_path(FIG_PATH)

with open(f"{project_dir}/sg_covid_impact/model_config.yaml", "r") as infile:
    out_params = yaml.safe_load(infile)["modelling"]
nuts1_focus = out_params["nuts1"]

# Lookups etc
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

my_vars = [
    "exposure_share_present",
    "exposure_share_lagged",
    "low_div_share_present",
    "low_div_share_lagged",
]

_SEC_KEEP = ["% tertiary", "% no qual", "Gross annual pay", "Emp rate", "ECI"]

exp_vars = ["exposure_share_present", "low_div_share_present"]
out_vars = ["cl_count_norm"]
secondary_vars = _SEC_KEEP


########
# Reading, processing, plotting and modelling
########

# Make variables
exp = make_exposure_share_variable()  # Exposure share
div = make_div_share_variable()  # low diversification share
cl = make_claimant_count_variable()  # Claimant count
secondary = make_secondary_variables()  # Secondary

# Bivariate correlations
# We will use this table for regressions and correlations
reg_table = make_regression_table(cl, exp, div, secondary)
tidy_agg_df = make_tidy_agg_table(
    reg_table, exp_vars, out_vars, secondary_vars, nuts_focus=nuts1_focus
)
bivariate_scatters = plot_variable_correlations(tidy_agg_df)
save_altair(bivariate_scatters, "bivariate_scatters", driver=driver, path=FIG_PATH)

correlation_evolution = plot_correlation_evolution(reg_table, nuts_focus=nuts1_focus)

# Correlation table
scot_reg_table = reg_table.loc[[x[0] != "S" for x in reg_table["geo_cd"]]]

corr_all = make_correlation_plot(scot_reg_table)
save_altair(corr_all, "correlation_table", driver=driver, path=FIG_PATH)

# Regression
mods = {}

# For each dependent variable we fit a model
for dep in ["cl_count", "cl_count_norm"]:
    for indep in ["exp", "div"]:
        mods[f"{dep}_{indep}"] = fit_regression(reg_table, dep, indep)

# Extract model results and concatenate
model_results = pd.concat([extract_model_results(v, name=k) for k, v in mods.items()])

# Plot model
model_selected = (
    model_results.reset_index(drop=False).loc[model_results.index.isin(my_vars)]
).reset_index(drop=True)

# Process model variables
model_selected["pred"] = [
    "exp share" if "exposure" in x else "low div share" for x in model_selected["index"]
]
model_selected["temporal"] = [
    "lagged" if "lagged" in x else "present" for x in model_selected["index"]
]

# Create plot with model coefficients
regression_plot = plot_model_coefficients(model_selected)

# # Combine with correlation evolution plot above
# modelling_results = alt.vconcat(correlation_evolution, regression_plot).resolve_scale(
#     color="independent"
# )

save_altair(regression_plot, "modelling_results", driver=driver, path=FIG_PATH)

# Conclude by exploring predictions based on current data

predicted_actual = combine_predicted_actual(
    make_predicted_values(mods, exp, div, secondary), cl
)

pred_ch = plot_predictions(predicted_actual.query("nuts1=='Scotland'"))

save_altair(pred_ch, "predicted_outputs", driver=driver, path=FIG_PATH)
