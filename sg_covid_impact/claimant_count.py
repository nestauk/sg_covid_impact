import pandas as pd
import logging
import re
import sg_covid_impact

project_dir = sg_covid_impact.project_dir

# _CLAIM_URL = "https://www.nomisweb.co.uk/api/v01/dataset/NM_162_1.data.csv?geography=1874854111,1874853904,1874853931,1874853936,1874853949,1874853952,1874853980,1874853984,1874854016,1874853894,1874853899,1874853901,1874853902,1874853914,1874854112,1874854113,1874853929,1874853959,1874853963,1874853970,1874853976,1874853990,1874853996,1874854026,1874854029,1874854033,1874853892,1874853907,1874853909,1874853933,1874853945,1874853947,1874853948,1874853954,1874853955,1874853966,1874853975,1874853985,1874854000...1874854002,1874854006,1874854025,1874854028,1874854037,1874853905,1874853917,1874853922,1874853926,1874853932,1874853943,1874853960,1874853967,1874853968,1874853977,1874853986,1874853988,1874854005,1874854010,1874854034,1874853900,1874853915,1874853927,1874853935,1874853951,1874853965,1874853973,1874854116,1874854003,1874854012,1874854014,1874854019,1874854031,1874854032,1874853897,1874853916,1874853918,1874853920,1874853924,1874853925,1874853930,1874853944,1874853956,1874853957,1874853961,1874853972,1874853974,1874853987,1874853992,1874854009,1874854013,1874854020,1874854030,1874853971,1874853889...1874853891,1874853895,1874853911,1874853919,1874853923,1874853928,1874853937,1874853941,1874853946,1874853950,1874853953,1874853958,1874853978,1874853979,1874853981,1874853983,1874853989,1874853995,1874853997,1874854007,1874854008,1874854023,1874854035,1874853893,1874853896,1874853898,1874853903,1874853906,1874853908,1874853910,1874853912,1874853913,1874853921,1874854114,1874853934,1874853938...1874853940,1874853942,1874853962,1874853964,1874853969,1874853982,1874853991,1874853993,1874853994,1874853998,1874853999,1874854004,1874854011,1874854015,1874854017,1874854018,1874854021,1874854022,1874854024,1874854027,1874854036,1874854038...1874854048,1874854115,1874854049...1874854069,1874854071...1874854099,1874854070,1874854100...1874854110&date=latestMINUS_PAR_-latest&gender=0&age=0&measure=1,2&measures=20100"
_CLAIM_URL = "https://www.nomisweb.co.uk/api/v01/dataset/NM_162_1.data.csv?geography=1811939329...1811939332,1811939334...1811939336,1811939338...1811939497,1811939499...1811939501,1811939503,1811939505...1811939507,1811939509...1811939517,1811939519,1811939520,1811939524...1811939570,1811939575...1811939599,1811939601...1811939628,1811939630...1811939634,1811939636...1811939647,1811939649,1811939655...1811939664,1811939667...1811939680,1811939682,1811939683,1811939685,1811939687...1811939704,1811939707,1811939708,1811939710,1811939712...1811939717,1811939719,1811939720,1811939722...1811939730,1811939757...1811939767&date=latestMINUS_PAR_-latest&gender=0&age=0&measure=1,2&measures=20100"


_CLAIM_FILE = f"{project_dir}/data/processed/claimant_counts.csv"


def fetch_claimant_data(loc):
    """Loads claimant data from NOMIS
    Args:
        loc (str): location of claimant file

    """
    return pd.read_csv(loc)


def get_claimant_data():
    """Get claimant data stored locally"""

    return pd.read_csv(_CLAIM_FILE)


def process_claimant_data(table):
    """Processes claimant data
    Args:
        table (df): dataframe with raw claimant data
    """
    table.columns = [x.lower() for x in table.columns]
    table["date"] = pd.to_datetime(table["date"], format="%Y-%m")

    rel_vars = ["date", "geography_name", "geography_code", "measure_name", "obs_value"]

    return table[rel_vars]


def get_month_delta():
    """Calculate month difference between latest available and beginning of
    relevant series (1st Jan 2019). We need this to construct a query going back
    latestMINUSdelta months.
    """
    # Only collect the latest cut of the data
    latest_url = re.sub("latestMINUS_PAR_-", "", _CLAIM_URL)
    claimant_latest = fetch_claimant_data(latest_url).pipe(process_claimant_data)

    # Get the date
    claimant_latest_date = claimant_latest["date"].max()

    # Calculate the month difference between latest and 1st January 2019
    diff_w_first_p = (
        (claimant_latest_date.year - 2019) * 12 + claimant_latest_date.month - 1
    )

    return str(diff_w_first_p)


def make_claimant_data():
    """Collect and process claimant data.
    Returns the processed dataset and the last month in the data
    """
    # Get month difference between latest month and
    month_delta = get_month_delta()

    # Build a query URL with the delta
    new_url = re.sub("_PAR_", month_delta, _CLAIM_URL)

    claimant_proc = fetch_claimant_data(new_url).pipe(process_claimant_data)

    # Extract last date
    last_date = str(claimant_proc["date"].max())

    return last_date, claimant_proc

def read_claimant_data():
    return pd.read_csv(_CLAIM_FILE)


if __name__ == "__main__":
    last_date, proc = make_claimant_data()

    logging.info(f"Saving claimant data, last date {last_date}")

    proc.to_csv(_CLAIM_FILE, index=False)
