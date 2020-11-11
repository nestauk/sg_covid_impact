# %%
"""
Collection of BRES and IDBR data from the NOMIS API
"""
import logging
from io import StringIO
from typing import Iterable, Tuple

import requests
import pandas as pd
from toolz import merge
import ratelim
import sg_covid_impact

logger = logging.getLogger(__name__)
CELL_LIMIT = 25_000
REQUESTS_PER_SECOND = 2
PROJECT_DIR = sg_covid_impact.project_dir


def get_data_id(dataset: str, year: int) -> Tuple[int, dict]:
    """Get NOMIS data ID and column meta-data from dataset-year combo

    NOMIS data-set ID's:
        141: UK Business Counts - local units by industry and employment
            size band (2010 onwards)
        172: Business Register and Employment Survey : open access
            (2015 onwards)
        189: Business Register and Employment Survey (excluding units
            registered for PAYE only) : open access (2009 to 2015)
    """
    if dataset == "IDBR":
        data_id = 141
        payload = {"employment_sizeband": 0, "legal_status": 0, "measures": 20100}
    elif dataset == "BRES" and year >= 2015:
        data_id = 189
        payload = {"employment_status": 4, "measure": 1, "measures": 20100}
    elif dataset == "BRES" and 2009 <= year < 2015:
        data_id = 172
        payload = {"employment_status": 4, "measure": 1, "measures": 20100}
    return data_id, payload


def get_geography_code(geo_type: str) -> dict:
    """ Get NOMIS geography query code from `geo_type`"""
    if geo_type == "LAUA":
        API_geo = {"geography": "TYPE434"}
    elif geo_type == "TTWA":
        API_geo = {"geography": "TYPE447"}
    elif geo_type.startswith("TYPE") and _check_geo_type_suffix(geo_type[4:]):
        API_geo = {"geography": geo_type}
    else:
        raise ValueError(f"`geo_type` value {geo_type} not valid")
    return API_geo


def get_sector_codes() -> dict:
    # 4 digit SIC query codes for NOMIS
    with open(f"{PROJECT_DIR}/data/aux/NOMIS_4SIC_codes.txt") as f:
        codes = f.read().rstrip("\n")
    return {"industry": codes}


def get_nomis(dataset: str, geo_type: str, year: int) -> Iterable:
    """Get BRES or IDBR datasets (SIC4) from NOMIS for given year and geography

    Args:
        dataset (str, {'BRES', 'IDBR'}): BRES or IDBR
        geo_type (str, {'TTWA', 'LAD', 'TYPE{int}'}): Geography type.
            'TTWA', 'LAD', or geography type to be passed straight to the API query.
            For example `TYPE450` will give 2013 NUTS2 areas.
        year (int): Year

    Returns:
        pandas.DataFrame
    """

    endpoint = "http://www.nomisweb.co.uk/api/v01/dataset/NM_{}_1.data.csv"

    # Data ID and varaiables to extract
    data_id, columns = get_data_id(dataset, year)

    fields = [
        "date_name",
        "geography_type",
        "geography_name",
        "geography_code",
        "industry_name",
        "obs_value",
        "obs_status_name",
        "record_count",
    ]
    select = {"select": ",".join(fields)}

    payload = merge(columns, get_geography_code(geo_type), get_sector_codes(), select)

    return query_nomis(endpoint.format(data_id), payload)


@ratelim.patient(REQUESTS_PER_SECOND, time_interval=1)
def query_nomis(
    endpoint: str, payload: dict, offset_size: int = CELL_LIMIT
) -> Iterable:
    """Query NOMIS api with ratelimiting and pagination

    Args:
        link (str): URL of NOMIS API query
        offset_size (int): Size of pagination chunks

    Returns:
        pandas.DataFrame
    """
    logger.info(f"Getting: {endpoint} with {payload}")

    offset = 0
    first_page = True
    records_left = 1  # dummy

    # While the final record we will obtain is below the total number of records:
    while records_left > 0:
        # Modify the query link with the offset
        response = requests.get(
            endpoint, params=merge(payload, {"recordoffset": str(offset)})
        )
        response.raise_for_status()
        if response.text == "":
            raise ValueError("Empty response for query")

        # Run query and store
        page = pd.read_csv(StringIO(response.text))
        yield page

        # Update the offset (next time we will query from this point)
        offset += offset_size

        # Get number of records from first iteration
        if first_page:
            total_records = page.RECORD_COUNT.values[0]
            logger.info(f"{total_records} to download")
            records_left = total_records
            first_page = False

        records_left -= offset_size
        logger.info(f"{records_left} records left")

    return


def _check_geo_type_suffix(x: str) -> int:
    """ Checks if `geo_type` suffix contains an `int` """
    try:
        return int(x)
    except ValueError:
        raise ValueError(f"`geo_type` suffix: '{x}' cannot be parsed as `int`.")


def tidy(df: pd.DataFrame) -> pd.DataFrame:
    """ Tidy-up data """
    return (  # Clean and enrich with industrial clusters
        df.rename(
            columns={
                "DATE_NAME": "year",
                "INDUSTRY_NAME": "SIC4",
                "GEOGRAPHY_TYPE": "geo_type",
                "OBS_VALUE": "value",
                "GEOGRAPHY_NAME": "geo_nm",
                "GEOGRAPHY_CODE": "geo_cd",
            }
        )
        .drop(["OBS_STATUS_NAME", "RECORD_COUNT"], 1)
        .assign(SIC4=lambda x: x["SIC4"].str.extract("([0-9]*)"))
        .fillna(0)
    )
