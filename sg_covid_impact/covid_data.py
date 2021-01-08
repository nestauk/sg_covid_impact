"""Fetch, save, and load Covid-19 case, death, and testing data from data.gov.uk."""
import requests
import pandas as pd
import logging
import sg_covid_impact

project_dir = sg_covid_impact.project_dir

_BASE_URL = "https://api.coronavirus.data.gov.uk/v2/data?areaType={geo}&{metrics}_&format=json".format
_GEO = "overview"
_METRICS = ["newCasesByPublishDate", "newDeaths28DaysByDeathDate", "newVirusTests"]
_COVID_FILE = f"{project_dir}/data/processed/covid_metrics.csv"


def fetch_covid(metrics, geo):
    """Fetch covid data from UK govt
    Args:
        metrics (list): metrics to fetch
        geo (str): geography to fetch
    Returns:
        A parsed and clean df
    """
    logging.info("Fetching covid data")
    # Concatenate metrics
    mq = []
    for q in metrics:
        mq.append(f"metric={q}")

    # Fill the query
    query_url = _BASE_URL(geo="overview", metrics="&".join(mq))

    # Fetch and parse
    response = requests.get(query_url)
    df = pd.DataFrame(response.json()["body"]).melt(
        id_vars=["date", "areaType", "areaCode", "areaName"],
        var_name="variable",
        value_name="value",
    )

    df["date"] = pd.to_datetime(df["date"])
    return df


def read_covid():
    """Read parsed covid table"""
    return pd.read_csv(_COVID_FILE, parse_dates=["date"])


if __name__ == "__main__":
    df = fetch_covid(_METRICS, _GEO)
    df.to_csv(_COVID_FILE, index=False)
