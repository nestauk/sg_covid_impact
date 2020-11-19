# %%
"""Metaflow pipeline to fetch salient terms for SIC divisions using Google trends."""
import json
import logging
import os
import subprocess
import sys
from itertools import product
from operator import attrgetter


def pip_install():
    path = f"{os.path.dirname(os.path.realpath(__file__))}/requirements.txt"
    path = "requirements.txt"
    output = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", path], capture_output=True
    )
    print(output.stderr)
    return output


pip_install()

import toolz.curried as t
import pandas as pd
from metaflow import (
    Run,
    FlowSpec,
    Parameter,
    step,
    JSONType,
    S3,
    resources,
    current,
)
from gtab import GTAB as GTAB_original
from tenacity import RetryError

from utils import set_gtab_timeframe, gtab_query, anchor_period_to_anchor_filename
from utils import GTAB as GTAB_patched


def format_results(df: pd.DataFrame, anchor_period: str) -> pd.DataFrame:
    return (
        df.assign(anchor_period=anchor_period)
        .melt(id_vars=["anchor_period"], ignore_index=False)
        .reset_index()
    )


class GoogleTrends(FlowSpec):
    terms = Parameter(
        "terms",
        help="List of terms to query",
        type=JSONType,
        default='["svelte", "react", "reframe", "angularjs"]',
    )
    chunksize = Parameter(
        "chunksize",
        help="Number of parameters to query with each batch machine",
        type=int,
        default=1_00,
    )

    anchor_periods = Parameter(
        "anchor_periods", help="", type=JSONType, default='["2020-01-01 2020-11-01"]'
    )

    anchor_locations = Parameter(
        "anchor_locations",
        help="S3 path to write and find anchors",
        type=str,
        default="s3://nesta-glass/anchorbanks",
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
        pip_install()
        if not isinstance(self.terms, list):
            raise ValueError(
                f"`terms` parameter `{self.terms}` is not a list of strings."
            )

        if self.test_mode:
            self.chunksize_ = 2
            self.terms_ = self.terms[:4]
            self.anchor_periods_ = self.anchor_periods[
                : min(2, len(self.anchor_periods))
            ]
        else:
            self.chunksize_ = self.chunksize
            self.terms_ = self.terms
            self.anchor_periods_ = self.anchor_periods

        if self.chunksize_ is None:
            self.chunksize_ = len(self.terms_)

        print(f"{len(self.terms_)} terms to query in chunks of {self.chunksize_}")
        print(self.anchor_periods_)

        self.term_chunks = list(t.partition(self.chunksize_, self.terms_))

        self.next(self.build_anchor, foreach="anchor_periods_")

    def _does_anchor_exist(self, anchor_period):
        with S3(s3root=self.anchor_locations) as s3:
            files = t.pipe(s3.list_paths(), t.map(attrgetter("key")), set)
        return anchor_period_to_anchor_filename(anchor_period) in files

    @step
    def build_anchor(self):
        pip_install()
        anchor_period = self.input

        gtab = GTAB_original()
        gtab.set_options(conn_config={"retries": 0})  # Defer retrying to our own logic

        gtab_name = set_gtab_timeframe(gtab, anchor_period)
        if not self._does_anchor_exist(anchor_period):
            logging.info(f"Creating anchorbank {gtab_name}")
            print(f"Creating anchorbank {gtab_name}")
            gtab.create_anchorbank()
            # Put on S3
            with S3() as s3:
                s3.put_files(
                    [
                        (
                            f"{self.anchor_locations}/{gtab_name}",
                            f"{gtab.dir_path}/output/google_anchorbanks/{gtab_name}",
                        )
                    ]
                )
        else:
            logging.info("Found existing anchorbank")
            print("Found existing anchorbank")

        # self.built_anchor = gtab_name
        self.built_anchor_period = anchor_period
        self.next(self.join_anchors)

    @step
    def join_anchors(self, inputs):
        # pip_install()
        self.missing_anchors = set(inputs[0].anchor_periods_) - set(
            [input_.built_anchor_period for input_ in inputs]
        )
        if len(self.missing_anchors) > 0:
            raise ValueError(f"Anchors are missing! {self.missing_anchors}")

        self.anchor_periods_ = [input_.built_anchor_period for input_ in inputs]
        self.term_chunks = inputs[0].term_chunks

        self.next(self.generate_parameter_grid)

    @step
    def generate_parameter_grid(self):
        pip_install()
        self.param_grid = list(product(self.term_chunks, self.anchor_periods_))

        # List of completed chunk numbers (for resumption after failure)
        self.s3_completed_key = "completed-chunks"
        with S3(run=self) as s3:
            s3.put(self.s3_completed_key, "[]")

        self.next(self.query_term_chunks)  # , foreach="param_grid")

    # @retry(times=3)
    @resources(cpu=2)
    @step
    def query_term_chunks(self):
        pip_install()

        data_run_id = current.origin_run_id or current.run_id

        # List of completed chunk numbers (for resumption after failure)
        with S3(run=Run(f"GoogleTrends/{data_run_id}")) as s3:
            completed_chunks = json.loads(s3.get(self.s3_completed_key).text)

        gtab = GTAB_patched()
        # Defer retrying to our own logic and sleep longer
        gtab.set_options(conn_config={"retries": 0}, gtab_config={"sleep": 1})
        for chunk_number, (term_chunk, anchor_period) in enumerate(self.param_grid):
            # Don't perform if completed
            if chunk_number in completed_chunks:
                continue

            # Where to store results for parameter set (to recover from failure)
            s3_chunk_key = f"chunk-{chunk_number}"

            gtab_name = set_gtab_timeframe(gtab, anchor_period)
            # fetch anchors
            with S3() as s3:
                with open(
                    f"{gtab.dir_path}/output/google_anchorbanks/{gtab_name}", "w"
                ) as f:
                    f.write(s3.get(f"{self.anchor_locations}/{gtab_name}").text)
            gtab.set_active_gtab(gtab_name)

            # Load any existing progress
            with S3(run=Run(f"GoogleTrends/{data_run_id}")) as s3:
                if s3_chunk_key in map(lambda x: x.key, s3.list_paths()):
                    results = pd.DataFrame(json.loads(s3.get(s3_chunk_key).text))
                else:
                    results = pd.DataFrame(
                        [], columns=["date", "anchor_period", "variable", "value"]
                    )

            completed_terms = results.variable.unique()
            counter = 0
            for term in filter(lambda term: term not in completed_terms, term_chunk):
                try:
                    if counter >= 1 and current.origin_run_id is None:
                        raise RetryError("FOOOO")
                    result = (
                        gtab_query(term, gtab)
                        .to_frame()
                        .pipe(format_results, anchor_period)
                    )
                    counter += 1
                except RetryError as e:
                    logging.error(e)
                    # Upload current results to s3
                    with S3(run=Run(f"GoogleTrends/{data_run_id}")) as s3:
                        s3.put(s3_chunk_key, serialise_to_jsons(results))
                    raise e

                results = results.append(result)

            output = results  # .pipe(format_results, anchor_period)

            with S3(run=Run(f"GoogleTrends/{data_run_id}")) as s3:
                # Upload output
                s3.put(s3_chunk_key + "-completed", serialise_to_jsons(output))
                # Mark chunk as completed
                completed_chunks.append(chunk_number)
                s3.put(
                    self.s3_completed_key,
                    json.dumps(completed_chunks),
                )

        # self.completed_chunks = True
        self.next(self.end)

    @step
    def end(self):
        pip_install()
        s3_keys = [
            f"chunk-{chunk_number}-completed"
            for chunk_number, _ in enumerate(self.param_grid)
        ]

        data_run_id = current.origin_run_id or current.run_id
        with S3(run=Run(f"GoogleTrends/{data_run_id}")) as s3:

            def get_chunk_output(s3_key):
                return pd.DataFrame(json.loads(s3.get(s3_key).text))

            self.output = pd.concat(map(get_chunk_output, s3_keys), axis=0)


def serialise_to_jsons(df: pd.DataFrame) -> str:
    """Serialise trends results to a JSON string."""
    return json.dumps(
        df.assign(date=lambda x: x.date.astype(str)).to_dict(orient="records")
    )


if __name__ == "__main__":
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        level=logging.INFO,
    )

    GoogleTrends()
