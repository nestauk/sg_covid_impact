# %%
import logging

import pandas as pd
from metaflow import namespace

from sg_covid_impact.utils.metaflow import cache_getter_fn
import sg_covid_impact


logger = logging.getLogger(__name__)
namespace(None)


@cache_getter_fn
def get_glass_house() -> pd.DataFrame:
    # TODO:
    logger.warn("This Glass-House data is a temporary placeholder")
    s3_path = "s3://nesta-glass/data/processed/glass/company_numbers.csv"
    return pd.read_csv(s3_path)
