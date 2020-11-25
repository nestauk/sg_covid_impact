import requests
import os
import logging
import re
import json
import pandas as pd

# from toolz.curried import pipe

import sg_covid_impact

project_dir = sg_covid_impact.project_dir

_SIC_OUTPUT_FILE = f"{project_dir}/data/raw/sic_2007.xls"
_SIC_LOOKUP_FILE = f"{project_dir}/data/raw/lookup.json"


def url():
    return sg_covid_impact.config["fetch_urls"]["sic_taxonomy"]


def extract_sic_code_description(table, var_name):
    """Extracts codes and descriptions from SIC table
    Args:
        table (pandas.DataFrame): summary of the SIC taxonomy
        var_name (str): level of SIC we want to extract a lookup for
    Returns:
        A lookup between the variable codes and their description
    """
    loc = list(table.columns).index(var_name)  # Find the location of class
    select = table.iloc[:, [loc, loc + 1]].dropna()  # Extract variable & description
    select.columns = [var_name, "description"]

    select[var_name] = [re.sub(r"\.", "", str(x)) for x in select[var_name]]
    name_lookup = select.set_index(var_name)["description"].to_dict()
    return name_lookup


def save_sic_taxonomy():
    logging.info("Saving sic taxonomy structure")
    response = requests.get(url())
    with open(_SIC_OUTPUT_FILE, "wb") as f:
        f.write(response.content)


def load_sic_taxonomy():  # Function to load taxonomy correctly
    return pd.read_excel(_SIC_OUTPUT_FILE, skiprows=1)


if __name__ == "__main__":

    if not os.path.exists(_SIC_OUTPUT_FILE):
        save_sic_taxonomy()

    if not os.path.exists(_SIC_LOOKUP_FILE):
        logging.info("Making code - name lookup")
        name_lookup = load_sic_taxonomy().pipe(extract_sic_code_description, "Division")
        with open(_SIC_LOOKUP_FILE, "w") as outfile:
            json.dump(name_lookup, outfile)
