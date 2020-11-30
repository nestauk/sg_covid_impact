import requests
import logging
from zipfile import ZipFile
from io import BytesIO
import os
import pandas as pd
import sg_covid_impact

project_dir = sg_covid_impact.project_dir

_GOOG_URL = "https://www.gstatic.com/covid19/mobility/Region_Mobility_Report_CSVs.zip"
_TARGET_DIR = f"{project_dir}/data/raw/google_footfall"
_COUNTRY = "GB"


def fetch_footfall_data():
    """Collects Google footfall data"""
    logging.info("Fetching Google footfall data")
    reg_g = requests.get(_GOOG_URL)
    z = ZipFile(BytesIO(reg_g.content))
    z.extractall(_TARGET_DIR)


def process_footfall_data(country_code):
    """Reads and processes country data for a country
    Args:
        country_code (str): country iso code
    """
    logging.info(f"Processing Google footfall data for {country_code}")
    c = pd.read_csv(f"{_TARGET_DIR}/2020_{country_code}_Region_Mobility_Report.csv")
    c = c.loc[c["sub_region_1"].isna()]
    c_long = c.dropna(axis=1).melt(
        id_vars=["country_region", "country_region_code", "date"]
    )
    c_long.to_csv(
        f"{project_dir}/data/processed/google_footfall_{country_code}.csv", index=False
    )


def load_uk_footfall():
    return pd.read_csv(f"{project_dir}/data/processed/google_footfall_gb.csv")


if __name__ == "__main__":
    if not os.path.exists(_TARGET_DIR):
        os.makedirs(_TARGET_DIR, exist_ok=True)
        fetch_footfall_data()
        process_footfall_data("gb")
