# Analysis of diversification opportunities
import yaml
import altair as alt
import pandas as pd
import numpy as np
from sg_covid_impact.descriptive import (
    get_date_label,
    make_section_division_lookup,
    read_official,
    calculate_sector_exposure,
    make_exposure_shares,
    make_exposure_shares_detailed,
    read_shape,
    plot_time_choro,
    load_sic_taxonomy,
    assign_nuts1_to_lad,
)
from sg_covid_impact.diversification import (
    make_month_range,
    load_predicted,
    extract_sectors,
    extract_network,
    make_sector_space_base,
    make_diversification_options,
    make_neighbor_shares,
    plot_exposure_neighbours,
    make_local_network,
    make_national_network,
    month_string_from_datetime,
    plot_divers_comparison,
    estimate_div_shares_geo,
)
from sg_covid_impact.make_sic_division import extract_sic_code_description
from sg_covid_impact.utils.altair_save_utils import (
    google_chrome_driver_setup,
    save_altair,
    # make_fig_path,
)

import sg_covid_impact

##########
# Preamble
##########
project_dir = sg_covid_impact.project_dir

alt.data_transformers.disable_max_rows()

driver = google_chrome_driver_setup()

FIG_PATH = f"{project_dir}/figures/scotland"
# make_fig_path(FIG_PATH)

with open(f"{project_dir}/sg_covid_impact/model_config.yaml", "r") as infile:
    out_params = yaml.safe_load(infile)["diversification"]
nuts1_focus = out_params["nuts1"]

# Lookups
_SECTION_DIVISION_LOOKUP, _SECTION_NAME_LOOKUP = make_section_division_lookup()
_DIVISION_NAME_LOOKUP = extract_sic_code_description(load_sic_taxonomy(), "Division")

# Variable names etc
net_titles = {
    "node_size_title": "Employment",
    "node_color_title": "Exposure to Covid",
    "edge_weight_title": "co-occurrences",
    "title": "Industry Space",
}

# Some local network params
local_networks = {
    "node_size_title": "Employment_share",
    "node_color_title": "Exposure to Covid",
    "edge_weight_title": "co-occurrences",
    "title": "",
}

###########
# Read, process and plot
###########

# Calculate sector exposures
exposures_ranked, weighted_scores = calculate_sector_exposure()

my_divisions = list(set(exposures_ranked["division"]))

division_month_exposure_dict = (
    exposures_ranked
    # Here we need to turn the timestamps into strings for merging
    .assign(month_str=lambda x: x["month_year"].apply(month_string_from_datetime))
    .set_index(["division", "month_str"])["rank"]
    .to_dict()
)
# Read official data
bres = read_official()

# Calculate exposure levels
exposure_levels = exposures_ranked.merge(bres, left_on="division", right_on="division")
exposure_levels["is_scot"] = [
    "Scotland" if n == "Scotland" else "Not Scotland" for n in exposure_levels["nuts1"]
]
exposure_lad_detailed = make_exposure_shares_detailed(exposure_levels, "geo_nm")

# Read shapefile
shapef = read_shape()

# Make sector space
pr = load_predicted()
pr_selected = pr[my_divisions]

t = extract_sectors(pr_selected, 0.5)
div_space = extract_network(t)
p, g, l = make_sector_space_base(sector_space=div_space, extra_edges=70)

# National network

scot_space = make_national_network(
    p, exposures_ranked, bres.query(f"nuts1=='{nuts1_focus}'"), g, **net_titles
)

save_altair(scot_space, f"sector_space_{nuts1_focus}", driver=driver, path=FIG_PATH)

# # Calculate and plot diversification options
neighb_shares = make_neighbor_shares(g, division_month_exposure_dict, "2021-01-01")

neigh_shares = plot_exposure_neighbours(neighb_shares)

save_altair(neigh_shares, "sector_diversification_options", driver, path=FIG_PATH)

# Diversification shares per LAD
monthly_diversification_rankings = pd.concat(
    [
        (
            make_diversification_options(
                g, division_month_exposure_dict, m, [7, 8, 9], [0, 1, 2, 3]
            )
            .sort_values("mean", ascending=False)
            .assign(
                divers_ranking=lambda x: pd.qcut(
                    # High values = high exposure with low diversification
                    x["mean"],
                    q=np.arange(0, 1.1, 0.25),
                    labels=False,
                )
            )
            .assign(month_year=m)
        )
        for m in make_month_range("2020-03-01", "2021-02-01")
    ]
)

# Plot Scottish trends for shares of employment in high exposure / low div sectors
# Calculate shares
diversification_scot = estimate_div_shares_geo(
    exposure_levels, monthly_diversification_rankings, "is_scot"
)
div_trends = plot_divers_comparison(diversification_scot, 2)

save_altair(div_trends, "div_trends", driver=driver, path=FIG_PATH)

# Plot LAD situation
diversification_lad_detailed = estimate_div_shares_geo(
    exposure_levels, monthly_diversification_rankings, "geo_cd"
)

diversification_lad_detailed["divers_ranking"] = diversification_lad_detailed[
    "divers_ranking"
].fillna("Less exposed")
# Calculate diversification shares
diversification_shares = make_exposure_shares(
    diversification_lad_detailed, geography="geo_cd", variable="divers_ranking"
).query("divers_ranking != 'Less exposed'")

diversification_nuts = diversification_shares.assign(
    nuts1=lambda x: x["geo_cd"].map(assign_nuts1_to_lad)
).query(f"nuts1=='{nuts1_focus}'")

# Plot maps
div_map_strip = [
    plot_time_choro(
        shapef,
        diversification_nuts,
        m,
        2,
        scale_type="quantile",
        exposure_var="divers_ranking",
        name="low diversification",
    ).properties(height=200, width=275, title=get_date_label(m))
    for m in out_params["months"]
]

div_map_plot = alt.hconcat(*div_map_strip).resolve_scale(color="shared")

# Plot local sector spaces
space_networks = [
    make_local_network(
        p, place, exposures_ranked, bres, g, month=m, **local_networks
    ).properties(height=200, width=275)
    for m, place in zip(out_params["months"], out_params["lads"])
]

space_networks_plot = alt.hconcat(*space_networks)

div_composite = alt.vconcat(div_map_plot, space_networks_plot).configure_view(
    strokeWidth=0
)

save_altair(div_composite, "geo_diversification_profiles", driver=driver, path=FIG_PATH)
