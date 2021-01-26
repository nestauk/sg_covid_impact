import requests
import os
import logging
import re
import json
import pandas as pd
import sg_covid_impact

project_dir = sg_covid_impact.project_dir

_SIC_OUTPUT_FILE = f"{project_dir}/data/raw/sic_2007.xls"
_SIC_LOOKUP_FILE = f"{project_dir}/data/processed/div_name_lookup.json"
_SIC_TAXONOMY_URL = "https://www.ons.gov.uk/file?uri=/methodology/classificationsandstandards/ukstandardindustrialclassificationofeconomicactivities/uksic2007/sic2007summaryofstructurtcm6.xls"


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
    return select.set_index(var_name)["description"].to_dict()


def save_sic_taxonomy():
    """Fetch SIC taxonomy and save as excel file"""
    response = requests.get(_SIC_TAXONOMY_URL)
    with open(_SIC_OUTPUT_FILE, "wb") as f:
        f.write(response.content)


def load_sic_taxonomy():
    """Load SIC taxonomy into a dataframe"""
    return pd.read_excel(
        _SIC_OUTPUT_FILE,
        skiprows=1,
        dtype={"Division": str, "Group": str, "Class": str, "Sub Class": str},
    )


def make_sic_lookups():
    """Produces SIC code - name lookups we use to label tables later
    Args:
        path (str): the path to the sic summary file
    Returns:
        Lookup between sic codes and sic descriptions
        Lookup between section names and sic descriptions
        Lookup between sic codes and corresponding sections
    """

    # SIC names to code lookup
    sic2007 = load_sic_taxonomy()
    sic4_name_lookup = extract_sic_code_description(sic2007, "Class")

    # Create a section to description lookup
    section_names = sic2007.dropna(axis=0, subset=["SECTION"]).iloc[:, :2]

    section_name_lookup = {
        s.strip(): s.strip()
        + f": {' '.join([x.capitalize() for x in descr.lower().split(' ')])}"
        for s, descr in zip(section_names["SECTION"], section_names["Unnamed: 1"])
    }
    # Division-sic4 lookup
    sic2007_ = sic2007.copy()

    sic2007_["SECTION"].fillna(method="ffill", inplace=True)
    sic2007_.dropna(axis=0, subset=["Class"], inplace=True)
    sic2007_["sic_4"] = [re.sub("\\.", "", x) for x in sic2007_["Class"]]
    sic2007_["section_descr"] = (
        sic2007_["SECTION"].apply(lambda x: x.strip()).map(section_name_lookup)
    )
    sic4_to_div_lookup = sic2007_.set_index("sic_4")["section_descr"].to_dict()

    return sic4_name_lookup, section_name_lookup, sic4_to_div_lookup


if __name__ == "__main__":

    if not os.path.exists(_SIC_OUTPUT_FILE):
        save_sic_taxonomy()

    if not os.path.exists(_SIC_LOOKUP_FILE):
        logging.info("Making code - name lookup")
        name_lookup = load_sic_taxonomy().pipe(extract_sic_code_description, "Division")
        with open(_SIC_LOOKUP_FILE, "w") as outfile:
            json.dump(name_lookup, outfile)
