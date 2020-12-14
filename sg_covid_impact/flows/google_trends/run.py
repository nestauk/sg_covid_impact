# %%
import logging
from pathlib import Path
from json import dumps
from sg_covid_impact import config
from sg_covid_impact.utils.metaflow import update_model_config, execute_flow
from sg_covid_impact.google_trends.get_search_trends import (
    load_salient_words,
    extract_salient_words,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":

    google_config = config["flows"]["google_search"]
    params = google_config["params"]
    anchor_periods = list(params["anchor_periods"].values())
    terms = load_salient_words().pipe(extract_salient_words, params["threshold"])

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
            # "--with": "batch:queue=job-queue-many-nesta-metaflow",
            # "--max-workers": "256"
            "--tag sg_covid_impact"
        },
    )

    google_config["run_id"] = run_id
    update_model_config(["flows", "google_search"], google_config)
