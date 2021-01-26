import logging
import subprocess
from itertools import chain
from json import dumps
from pathlib import Path
from pickle import load
from typing import List

import toolz.curried as t

from sg_covid_impact import config, project_dir, extract_salient_terms
from sg_covid_impact.utils.metaflow import update_model_config, execute_flow

from sg_covid_impact.google_trends.get_search_trends import (
    load_salient_words,
    extract_salient_words,
)

logger = logging.getLogger(__name__)


def get_term_list() -> List[str]:
    """Gets list of terms to query trends for."""
    term_set1 = (
        load_salient_words()
        .pipe(extract_salient_words, params["term_salience_threshold"])
        .keyword.pipe(set)
    )

    path = Path(f"{project_dir}/data/processed/salient_words_selected.p").resolve()
    if not path.exists():
        script_path = Path(extract_salient_terms.__file__).resolve()
        subprocess.run(["python", str(script_path)], capture_output=True, check=True)

    with open(path, "rb") as fp:
        term_set2 = t.pipe(fp, load, lambda x: x.values(), chain.from_iterable, set)

    return sorted(list(term_set1 | term_set2))


if __name__ == "__main__":

    google_config = config["flows"]["google_search"]
    params = google_config["params"]
    anchor_periods = list(params["anchor_periods"].values())

    terms = get_term_list()

    cmd_params = {
        "--anchor_periods": dumps(anchor_periods),
        "--terms": dumps(terms),
        "--test_mode": str(params["test_mode"]),
    }
    flow_file = Path(__file__).resolve().parents[0] / "gtab_flow_linear.py"
    run_id = execute_flow(
        flow_file,
        cmd_params,
        metaflow_args={
            "--package-suffixes": ".py,.txt",
            # "--metadata": "local",
            # "--datastore": "local"
            "--with": "batch:queue=job-queue-many-nesta-metaflow",
            "--max-workers": "1"
            # "--tag": "sg_covid_impact"
        },
    )

    google_config["run_id"] = run_id
    update_model_config(["flows", "google_search"], google_config)
