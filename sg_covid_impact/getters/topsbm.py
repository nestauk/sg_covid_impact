"""Data getters for Glass business website data."""
import logging
import pickle
from pathlib import Path
from typing import Dict

import pandas as pd
from metaflow import namespace

from sg_covid_impact.utils.metaflow import flow_getter
import sg_covid_impact


OUTPUT_DIR = Path(f"{sg_covid_impact.project_dir}/data/interim/topsbm_models")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
namespace(None)


def run_ids() -> Dict[str, int]:
    """Get `run_id` for flow

    NOTE: This is loaded from __init__.py not from file
    """
    config = sg_covid_impact.config["flows"]["notice_topics"]
    return {k: config[k]["run_id"] for k in config.keys()}


# @cache_getter_fn
def get_topsbm_all() -> pd.DataFrame:
    """."""
    output_path = OUTPUT_DIR / "all.pkl"
    if not output_path.exists():
        data = flow_getter("TopSBMFlow", run_id=run_ids()["all"])
        output = {"model": data.model, "titles": data.titles}
        with output_path.open("wb") as f:
            pickle.dump(output, f)
        return output
    else:
        logger.info("Loading cached value")
        with output_path.open("rb") as f:
            return pickle.load(f)


# @cache_getter_fn
def get_topsbm_scotland() -> pd.DataFrame:
    """."""
    output_path = OUTPUT_DIR / "scotland.pkl"
    if not output_path.exists():
        data = flow_getter("TopSBMFlow", run_id=run_ids()["scotland"])
        output = {"model": data.model, "titles": data.titles}
        with output_path.open("wb") as f:
            pickle.dump(output, f)
        return output
    else:
        logger.info("Loading cached value")
        with output_path.open("rb") as f:
            return pickle.load(f)


# @cache_getter_fn
def get_topsbm_section() -> pd.DataFrame:
    """."""
    output_path = OUTPUT_DIR / "section.pkl"
    if not output_path.exists():
        data = flow_getter("TopSBMGroupedFlow", run_id=run_ids()["section"])
        output = {"models": data.models, "titles": data.titles}
        with output_path.open("wb") as f:
            pickle.dump(output, f)
        return output
    else:
        logger.info("Loading cached value")
        with output_path.open("rb") as f:
            return pickle.load(f)
