# Compare modelled and actual claimant counts

from sg_covid_impact.claimant_count import get_claimant_data
from sg_covid_impact.utils.altair_save_utils import (
    google_chrome_driver_setup,
    save_altair,
)

import altair as alt
import pandas as pd
import numpy as np
import sg_covid_impact

project_dir = sg_covid_impact.project_dir
driver = google_chrome_driver_setup()

names_lookup = {
    "cl_count": "Claimant count",
    "cl_count_norm": "Claimant count (normalised)",
    "div": "Low diversification share",
    "exp": "Low exposure share",
    "jan_pred": "Predicted (January)",
    "jan_value": "Actual (January)",
}


def make_predicted_actual():
    """Reads our predictions and january actuals"""

    pred = pd.read_csv(f"{project_dir}/data/processed/predicted_actual.csv").iloc[:, 1:]

    actual = (
        pred.query("variable=='actual'")
        .rename(columns={"value": "dec_value"})
        .drop(axis=1, labels=["variable", "nuts1"])
    )

    return pred, actual


def compare_pred_actual() -> pd.DataFrame:
    """Reads and processes data and compares actual / predicted results"""

    pred, dec = make_predicted_actual()
    jan = make_claimant_data()
    comparison = make_comparison_table(pred, dec, jan)

    comp_stats = calculate_comparison_statistics(comparison)
    comp_stats.to_markdown(
        f"{project_dir}/data/processed/pred_results.md", index=False,
        floatfmt='.3f'
    )

    ch = plot_comparisons(comparison)
    save_altair(ch, "prediction_comparison", driver)


def make_comparison_table(
    pred: pd.DataFrame, dec: pd.DataFrame, jan: pd.DataFrame
) -> pd.DataFrame:
    """Combines predicted, january & december data
    Args:
        pred: predicted values for jan
        dec: actual values for december
        jan: actual values for jan

    """
    pred_act = (
        pred.query("variable!='actual'")
        .rename(columns={"value": "jan_pred"})
        .merge(dec, on=["geo_cd", "geo_nm", "output"])
        .merge(jan, on=["geo_cd", "geo_nm", "output"])
        .assign(real_diff=lambda df: df["jan_value"] - df["dec_value"])
        .assign(pred_diff=lambda df: df["jan_pred"] - df["dec_value"])
        .query("nuts1=='Scotland'")
        .reset_index(drop=True)
        .assign(
            agree=lambda df: [
                np.sign(x) == np.sign(y)
                for x, y in zip(df["pred_diff"], df["real_diff"])
            ]
        )
    )

    return pred_act


def get_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates some comparisons between january (predicted & actual) & dec values"""

    val_corrs = df[["jan_pred", "jan_value"]].corr().values[0][1]
    #agree_share = df["agree"].mean()

    mse_val = np.sum((df["jan_pred"] - df["jan_value"]) ** 2)

    out = pd.Series(
        [val_corrs, mse_val],
        index=["Correlation", "Mean Squared Error"],
    )
    return out


def calculate_comparison_statistics(comparison: pd.DataFrame) -> pd.DataFrame:
    """Calculates comparison statistics"""
    comp_stats = (
        comparison.groupby(["output", "variable"])
        .apply(lambda df: get_comparison(df))
        .reset_index(drop=False)
        .assign(output=lambda df: df["output"].map(names_lookup))
        .assign(variable=lambda df: df["variable"].map(names_lookup))
    )
    return comp_stats


def make_claimant_data():
    """Makes claimant data"""
    cl = get_claimant_data()

    cl = cl.query(
        "measure_name=='Claimants as a proportion of residents aged 16-64'"
    ).assign(month=lambda df: [int(x.split("-")[1]) for x in df["date"]])

    cl_rescaler = (
        cl.loc[[x.split("-")[0] == "2019" for x in cl["date"]]]
        .set_index(["geography_code", "month"])["obs_value"]
        .to_dict()
    )

    cl["norm"] = [
        cl_rescaler[(r["geography_code"], r["month"])] for _, r in cl.iterrows()
    ]

    cl = (
        cl.query("measure_name=='Claimants as a proportion of residents aged 16-64'")
        .assign(month=lambda df: [int(x.split("-")[1]) for x in df["date"]])
        .assign(
            resc=lambda df: [
                cl_rescaler[(r["geography_code"], r["month"])] for _, r in df.iterrows()
            ]
        )
        .assign(norm=lambda df: df["obs_value"] / df["resc"])
        .query("date=='2021-01-01'")
        .rename(
            columns={
                "geography_name": "geo_nm",
                "geography_code": "geo_cd",
                "obs_value": "cl_count",
                "norm": "cl_count_norm",
            }
        )
        .drop(axis=1, labels=["month", "measure_name", "date", "resc"])
        .melt(id_vars=["geo_cd", "geo_nm"], var_name="output", value_name="jan_value")
    )

    return cl


def plot_comparisons(comp_table: pd.DataFrame) -> alt.Chart:
    """Plots comparison chart"""

    plot_table = (
        comp_table[["geo_cd", "geo_nm", "jan_value", "jan_pred", "variable", "output"]]
        .melt(id_vars=["geo_cd", "geo_nm", "variable", "output"], var_name="pred_type")
        .assign(variable=lambda df: df["variable"].map(names_lookup))
        .assign(output=lambda df: df["output"].map(names_lookup))
        .assign(pred_type=lambda df: df["pred_type"].map(names_lookup))
    )

    sort_lads = (
        plot_table.query("pred_type=='Actual (January)'")
        .query("output=='Claimant count (normalised)'")
        .drop_duplicates("geo_nm")
        .sort_values("value", ascending=False)["geo_nm"]
        .to_list()
    )

    ch = (
        (
            alt.Chart(plot_table)
            .mark_point(filled=True)
            .encode(
                y=alt.Y("geo_nm", sort=sort_lads, title=None),
                x="value",
                color=alt.Color("pred_type", title="Value type"),
                row=alt.Row("variable", title="Predictor"),
                column=alt.Column("output", title="Output"),
            )
        )
        .properties(width=200, height=350)
        .resolve_scale(x="independent")
    )
    return ch


if __name__ == "__main__":
    compare_pred_actual()
