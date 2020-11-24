import requests
import os
import logging
import sg_covid_impact
import re
import pandas as pd

project_dir = sg_covid_impact.project_dir

def url():
    return sg_covid_impact.config['fetch_urls']['sic_taxonomy'] 

def extract_sic_code_description(table, var_name, var_name_tidy):
    """Extracts codes and descriptions from SIC table
    Args:
        table (pandas.DataFrame): summary of the SIC taxonomy
        var_name (str): level of SIC we want to extract a lookup for
        var_name_tidy (str): name for the variable code
    Returns:
        A lookup between the variable codes and their description
    """
    loc = list(table.columns).index(var_name)  # Find the location of class
    select = table.iloc[:, [loc, loc + 1]].dropna()  # Extract variable & description
    select.columns = [var_name, "description"]

    select[var_name_tidy] = [re.sub(r"\.", "", str(x)) for x in select[var_name]]
    name_lookup = select.set_index(var_name_tidy)["description"].to_dict()
    return name_lookup


def main():
    logging.info("Saving sic taxonomy structure")
    response = requests.get(url())
    with open(f"{project_dir}/data/aux/sic_2007.xls",'wb') as f:
        f.write(response.content)

if __name__=='__main__':

    if os.path.exists(f"{project_dir}/data/aux/sic_2007.xls") is False:
        main()



