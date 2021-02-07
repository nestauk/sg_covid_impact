# %%
import logging
from pathlib import Path

from sg_covid_impact import config
from sg_covid_impact.utils.metaflow import update_model_config, execute_flow

logger = logging.getLogger(__name__)


if __name__ == "__main__":

    flow_config = config["flows"]["notice_tokens"]
    params = flow_config["params"]

    cmd_params = {
        "--n-gram": str(params["n_gram"]),
        "--test_mode": str(params["test_mode"]),
    }
    flow_file = Path(__file__).resolve().parents[0] / "notice_nlp.py"
    run_id = execute_flow(flow_file, cmd_params, metaflow_args={})

    flow_config["run_id"] = run_id
    update_model_config(["flows", "notice_tokens"], flow_config)
