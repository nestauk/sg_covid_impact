# %%
"""Metaflow pipeline to fetch salient terms for SIC divisions using Google trends."""
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
from metaflow import FlowSpec, Parameter, step, JSONType, S3
from gtab import GTAB

from utils import set_gtab_timeframe, gtab_query, anchor_period_to_anchor_filename


class GoogleTrends(FlowSpec):
    terms = Parameter(
        "terms",
        help="List of terms to query",
        type=JSONType,
        default='["svelte", "react"]',
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

        self.term_chunks = t.partition(self.chunksize_, self.terms_)

        self.next(self.build_anchor, foreach="anchor_periods_")

    def _does_anchor_exist(self, anchor_period):
        with S3(s3root=self.anchor_locations) as s3:
            files = t.pipe(s3.list_paths(), t.map(attrgetter("key")), set)
        return anchor_period_to_anchor_filename(anchor_period) in files

    @step
    def build_anchor(self):
        pip_install()
        anchor_period = self.input

        gtab = GTAB()
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
            logging.info(f"Found existing anchorbank")
            print(f"Found existing anchorbank")

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
        self.next(self.query_term_chunks, foreach="param_grid")

    @step
    def query_term_chunks(self):
        pip_install()

        term_chunk, anchor_period = self.input
        gtab = GTAB()
        gtab_name = set_gtab_timeframe(gtab, anchor_period)
        # fetch anchors
        with S3() as s3:
            with open(
                f"{gtab.dir_path}/output/google_anchorbanks/{gtab_name}", "w"
            ) as f:
                f.write(s3.get(f"{self.anchor_locations}/{gtab_name}").text)
        gtab.set_active_gtab(gtab_name)

        self.output = (
            pd.concat(map(lambda x: gtab_query(x, gtab), term_chunk), axis=1)
            .assign(anchor_period=anchor_period)
            .melt(id_vars=["anchor_period"], ignore_index=False)
        )

        self.next(self.join_outputs)

    @step
    def join_outputs(self, inputs):
        pip_install()
        self.output = pd.concat([input_.output for input_ in inputs], axis=0)
        self.next(self.end)

    @step
    def end(self):
        """ """
        pass


if __name__ == "__main__":
    # logging.basicConfig(
    #     handlers=[logging.StreamHandler()],
    #     level=logging.DEBUG,
    # )

    GoogleTrends()
