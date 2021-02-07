# Charts for Scotland analysis
import yaml
import os
import altair as alt
import calendar
from sg_covid_impact.descriptive import (
    make_section_division_lookup,
    load_sic_taxonomy,
    read_claimant_counts,
    plot_national_comparison,
    claimant_count_norm,
    plot_trend_point,
    plot_claimant_trend_all_nuts,
    read_search_trends,
    search_trend_norm,
    plot_keyword_tends_chart,
    read_official,
    calculate_sector_exposure,
    make_exposure_shares_detailed,
    plot_emp_shares_specialisation,
    make_high_exposure,
    read_shape,
    assign_nuts1_to_lad,
    plot_time_choro,
    plot_area_composition,
    plot_ranked_exposures,
    make_exposure_shares,
)
from sg_covid_impact.utils.altair_save_utils import (
    google_chrome_driver_setup,
    save_altair,
)
from sg_covid_impact.make_sic_division import extract_sic_code_description

import sg_covid_impact

project_dir = sg_covid_impact.project_dir

# Prep
alt.data_transformers.disable_max_rows()

driver = google_chrome_driver_setup()

# Fig paths
FIG_PATH = f"{project_dir}/figures/scotland"

# Checks if the right paths exist and if not creates them when imported
os.makedirs(f"{FIG_PATH}/png", exist_ok=True)
os.makedirs(f"{FIG_PATH}/html", exist_ok=True)

# model config
with open(f"{project_dir}/sg_covid_impact/model_config.yaml", "r") as infile:
    out_params = yaml.safe_load(infile)["descriptive"]

nuts1_focus = out_params["nuts1"]


# Lookups
_SECTION_DIVISION_LOOKUP, _SECTION_NAME_LOOKUP = make_section_division_lookup()

_DIVISION_NAME_LOOKUP = extract_sic_code_description(load_sic_taxonomy(), "Division")

# Read and plot claimant counts
cl = read_claimant_counts()
cl_norm = claimant_count_norm(cl)
claimant_nuts1 = plot_trend_point(
    cl_norm.query(f"nuts1=='{nuts1_focus}'"), x_axis="yearmonth(date)"
)

save_altair(claimant_nuts1, f"claimant_counts_{nuts1_focus}", driver, path=FIG_PATH)

cl_trend = plot_claimant_trend_all_nuts(cl_norm)
save_altair(cl_trend, "claimant_counts_nuts1", driver, path=FIG_PATH)

# Read, process and plot search trends
d = read_search_trends()

trends_normalised = search_trend_norm(d)

month_trends = plot_keyword_tends_chart(trends_normalised)

save_altair(month_trends, "keyword_trends", driver=driver, path=FIG_PATH)

# Calculate sector exposures

exposures_ranked, keyword_weights = calculate_sector_exposure()

ranked_ch = plot_ranked_exposures(exposures_ranked)

save_altair(ranked_ch, "sector_exposures", driver=driver, path=FIG_PATH)

# Read official data
bres = read_official()

exposure_levels = exposures_ranked.merge(bres, left_on="division", right_on="division")

exposure_lad = make_exposure_shares(exposure_levels)

# Analysis of national composition
exposure_levels_ = exposure_levels.copy()
exposure_levels_nat_comp = make_exposure_shares_detailed(exposure_levels_, "nuts1")

# Compare evolution and composition of exposure in / out of Scotland
exposure_levels_nat_comp["Country"] = [
    "Scotland" if x == "Scotland" else "Not Scotland"
    for x in exposure_levels_nat_comp["nuts1"]
]

evol_chart = plot_national_comparison(exposure_levels_nat_comp, "Country")

save_altair(evol_chart, "national_exposure_evolution", driver, FIG_PATH)

nat_exp = plot_emp_shares_specialisation(
    exposure_levels_nat_comp, month="2021-01-01", nuts1=nuts1_focus
)

save_altair(
    nat_exp.properties(title=f"{nuts1_focus}, January 2021"),
    f"exposure_shares_{nuts1_focus}",
    driver=driver,
    path=FIG_PATH,
)

# Exposure by LAD
exposure_lad_detailed = make_exposure_shares_detailed(exposure_levels, "geo_nm")

high_exposure_nuts1 = make_high_exposure(
    make_exposure_shares(exposure_levels.query(f"nuts1=='{nuts1_focus}'"))
)

mean_high_exposure = (
    high_exposure_nuts1.query("month_year>'2020-03-01'")
    .groupby(["geo_nm"])["share"]
    .mean()
    .to_dict()
)
high_exposure_nuts1["mean_high_exposure"] = high_exposure_nuts1["geo_nm"].map(
    mean_high_exposure
)

exp_share_vars = {
    "geo_var": "geo_nm",
    "x_axis": "yearmonth(month_year)",
    "y_axis": "share",
    "y_title": "Share high exposure",
    "color": "mean_high_exposure",
}

exposure_trend = plot_trend_point(
    high_exposure_nuts1.query("month_year>'2020-02-01'"), **exp_share_vars
).properties(width=550, height=150)

save_altair(exposure_trend, "exposure_trend_lads", driver=driver, path=FIG_PATH)

# Maps
shapef = read_shape()
exposure_lad_codes = make_exposure_shares(exposure_levels, "geo_cd")
exposure_lad_codes["nuts1"] = exposure_lad_codes["geo_cd"].map(assign_nuts1_to_lad)
exposure_lad_codes_nuts1 = exposure_lad_codes.query(f"nuts1=='{nuts1_focus}'")

ms = alt.hconcat(
    *[
        plot_time_choro(
            shapef, exposure_lad_codes_nuts1, m, 8, scale_type="quantile"
        ).properties(
            height=200, width=275, title=calendar.month_abbr[int(m.split("-")[1])]
        )
        for m in out_params["months"]
    ]
)

# Profiles
profiles = [
    plot_area_composition(
        exposure_lad_detailed,
        month=month,
        interactive=False,
        area=area,
        legend_columns=5,
    ).properties(height=200, width=250)
    for area, month in zip(out_params["lads"], out_params["months"])
]

profiles_series = alt.hconcat(*profiles).resolve_scale(color="shared")

map_profiles = alt.vconcat(ms, profiles_series).configure_view(strokeWidth=0)

save_altair(map_profiles, f"geo_profiles_{nuts1_focus}", driver=driver, path=FIG_PATH)
