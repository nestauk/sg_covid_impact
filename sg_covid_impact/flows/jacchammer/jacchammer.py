# %%
"""Metaflow pipeline to fuzzy match two name sets.

TODO: refactor into research_daps

TODO: Run remotely and in isolated environment. Currently dependency on
`sg_covid_impact` and setting of `self.tmp_dir` prevents this.
"""
import logging
from pathlib import Path

from cytoolz.curried import curry, pipe
from metaflow import FlowSpec, Parameter, step, current, namespace
from jacc_hammer.fuzzy_hash import (
    Cos_config,
    Fuzzy_config,
    match_names_stream,
    stream_sim_chunks_to_hdf,
)
from jacc_hammer.name_clean import preproc_names
from jacc_hammer.top_matches import get_top_matches_chunked

from sg_covid_impact import project_dir
from sg_covid_impact.utils.metaflow import flow_getter


class GlassHouseMatch(FlowSpec):
    """ Match glass to Companies House """

    # TODO: Understand the best way to consistently chain/combine flows
    companies_house_flow_id = Parameter(
        "CH-flow-id",
        help="Metaflow run ID to provide CH data",
        default=None,
        type=int,
    )
    glass_flow_id = Parameter(
        "glass-flow-id",
        help="Metaflow run ID to provide glass data",
        default=None,
        type=int,
    )

    test_mode = Parameter(
        "test_mode",
        help="Whether to run in test mode (on a small subset of data)",
        type=bool,
        default=True,
    )

    @step
    def start(self):
        """ Load raw data """

        namespace(None)

        # TODO check both test_mode parameters agree
        logging.info(self.test_mode)

        # TODO optional ID loading of dependent flows
        # TODO check parameters agree
        logging.info(f"{self.glass_flow_id}")
        glass = flow_getter("GlassMergeMainDumpFlow", run_id=self.glass_flow_id)
        logging.info(f"{self.companies_house_flow_id}")
        ch = flow_getter(
            "CompaniesHouseMergeDumpFlow", run_id=self.companies_house_flow_id
        )

        run_id = current.origin_run_id or current.run_id
        self.tmp_dir = Path(
            f"{project_dir}/data/interim/{current.flow_name}/{run_id}"
        ).resolve()
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

        if self.test_mode:
            nrows = 10_000
            logging.warning(
                f"TEST MODE: Constraining to first {nrows} orgs or {nrows} rows..."
            )
        else:
            nrows = None

        self.names_y = (
            glass.organisation[["org_id", "name"]].head(nrows).set_index("org_id").name
        )
        self.names_x = (
            ch.organisationname[["company_number", "name"]]
            .head(nrows)
            .drop_duplicates(["company_number", "name"])
            .set_index("company_number")
            .name
        )

        self.next(self.process_names)

    @step
    def process_names(self):
        """ Pre-process names """
        self.names = [
            name.pipe(preproc_names).dropna()
            for i, name in enumerate([self.names_x, self.names_y])
        ]
        self.next(self.match)

    @step
    def match(self):
        """ The core fuzzy matching algorithm """
        cos_config = Cos_config()
        fuzzy_config = Fuzzy_config(num_perm=128)
        match_config = dict(
            threshold=33,
            chunksize=100,
            cos_config=cos_config,
            fuzzy_config=fuzzy_config,
            tmp_dir=self.tmp_dir,
        )
        self.f_fuzzy_similarities = f"{self.tmp_dir}/fuzzy_similarities"
        out = pipe(
            list(map(lambda x: x.values, self.names)),
            curry(match_names_stream, **match_config),
            curry(stream_sim_chunks_to_hdf, fout=self.f_fuzzy_similarities),
        )
        assert out == self.f_fuzzy_similarities, out
        self.next(self.find_top_matches)

    @step
    def find_top_matches(self):
        """ Find the top matches for each organisation """
        chunksize = 1e7

        self.top_matches = get_top_matches_chunked(
            self.f_fuzzy_similarities, chunksize=chunksize, tmp_dir=self.tmp_dir
        )

        self.next(self.end)

    @step
    def end(self):
        """ """
        self.company_numbers = (
            self.top_matches.merge(
                self.names_y.reset_index(),
                left_on="y",
                right_index=True,
                validate="1:1",
            )
            .merge(
                self.names_x.reset_index(),
                left_on="x",
                right_index=True,
                validate="m:1",
            )
            .drop(["x", "y"], axis=1)
        )


if __name__ == "__main__":
    logging.basicConfig(
        handlers=[logging.StreamHandler(), logging.FileHandler("log.log")],
        level=logging.INFO,
    )
    GlassHouseMatch()
