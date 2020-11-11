# %%
""" Metaflow pipeline to fetch IDBR and BRES data """
import logging

from itertools import chain
from typing import Iterable
import toolz.curried as t
import pandas as pd
from metaflow import FlowSpec, Parameter, step, JSONType
import sg_covid_impact
from utils import get_nomis, tidy

logger = logging.getLogger(__name__)
TEST_N_PAGES = 3


class Nomis(FlowSpec):
    """Fetch IDBR and BRES data from NOMIS API

    Artifacts:
        geo_type (str): Parameter specifying geography type
        years (JSONType): Parameter specifying list of years to query NOMIS for
        test_mode (bool): If True, only fetches a subset of data
        IDBR (pandas.DataFrame): IDBR data extracted from NOMIS API
        BRES (pandas.DataFrame): BRES data extracted from NOMIS API
    """

    geo_type = Parameter(
        "geo_type", help="Type of aggregate geography", type=str, default="LAUA"
    )
    years = Parameter(
        "years",
        help="List of years to query NOMIS with",
        type=JSONType,
        default="[2018]",
    )
    test_mode = Parameter(
        "test_mode",
        help="Whether to run in test mode (fetch a subset of data)",
        type=bool,
        default=True,
    )

    @step
    def start(self):
        """ """
        logging.info(f"Years: {self.years}")
        logging.info(f"Geography type: {self.geo_type}")
        if not isinstance(self.years, list):
            raise ValueError(f"`year` parameter `{self.years}`is not a list")
        self.next(self.fetch_bres)

    @step
    def fetch_bres(self):
        """ Fetch BRES data """
        iter_ = (get_nomis("BRES", self.geo_type, year) for year in self.years)

        self.BRES = t.pipe(
            iter_,
            chain.from_iterable,
            self._test_check,
            pd.concat,
            tidy,
        )
        self.next(self.fetch_idbr)

    @step
    def fetch_idbr(self):
        """ Fetch IDBR data """
        iter_ = (get_nomis("IDBR", self.geo_type, year) for year in self.years)

        self.IDBR = t.pipe(
            iter_,
            chain.from_iterable,
            self._test_check,
            pd.concat,
            tidy,
        )
        self.next(self.end)

    @step
    def end(self):
        """ """
        pass

    def _test_check(self, iter_: Iterable) -> Iterable:
        if self.test_mode:
            logging.warning("Running in test mode")
            iter_ = t.take(TEST_N_PAGES, iter_)
        return iter_


if __name__ == "__main__":
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        level=logging.DEBUG,
    )

    Nomis()
