# %%
import logging
from pathlib import Path
from json import dumps
from sg_covid_impact import config
from sg_covid_impact.utils.metaflow import update_model_config, execute_flow

logger = logging.getLogger(__name__)


if __name__ == "__main__":

    google_config = config["flows"]["google_search"]
    params = google_config["params"]
    anchor_periods = list(params["anchor_periods"].values())
    with open("terms.txt", "r") as f:
        terms = f.read().split("\n")

    cmd_params = {
        "--anchor_periods": dumps(anchor_periods),
        "--terms": dumps(terms),
        "--test_mode": str(params["test_mode"]),
        "--with": "batch:queue=job-queue-many-nesta-metaflow",
        # "--max-workers": "256"
    }
    flow_file = Path(__file__).resolve().parents[0] / "gtab_flow_linear.py"
    run_id = execute_flow(
        flow_file,
        cmd_params,
        metaflow_args={
            "--package-suffixes": ".py,.txt",
            # "--metadata": "local",
            # "--datastore": "local"
        },
    )

    google_config["run_id"] = run_id
    update_model_config(["flows", "google_search"], google_config)
