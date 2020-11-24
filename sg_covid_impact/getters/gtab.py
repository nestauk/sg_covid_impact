# %%
import json

import pandas as pd
import metaflow as mf
import toolz.curried as t

from sg_covid_impact.utils.metaflow import flow_getter, cache_getter_fn
import sg_covid_impact


def run_id() -> int:
    """Get `run_id` for flow

    NOTE: This is loaded from __init__.py not from file
    """
    return sg_covid_impact.config["flows"]["google_search"]["run_id"]


def get_trends(run_id_: int = -1) -> pd.DataFrame:
    if run_id_ == -1:
        run_id_ = run_id()

    s3 = mf.S3(run=mf.Run(f"GoogleTrends/{run_id_}"))

    return t.pipe(
        s3.list_paths(),
        t.map(lambda x: x.key),
        t.filter(lambda x: "-completed" in x),
        s3.get_many,
        t.map(t.compose(pd.DataFrame, json.loads, lambda x: x.text)),
        pd.concat,
    ).drop("index", 1)
