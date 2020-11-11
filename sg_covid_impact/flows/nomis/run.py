# %%
import logging
from pathlib import Path
from json import dumps
from sg_covid_impact import config
from sg_covid_impact.utils.metaflow import update_model_config, execute_flow

logger = logging.getLogger(__name__)


if __name__ == "__main__":

    nomis_config = config["flows"]["nomis"]
    params = nomis_config["params"]

    cmd_params = {
        "--years": dumps(params["years"]),
        "--test_mode": str(params["test_mode"]),
    }
    flow_file = Path(__file__).resolve().parents[0] / "nomis.py"
    run_id = execute_flow(flow_file, cmd_params)

    nomis_config["run_id"] = run_id
    update_model_config(["flows", "nomis"], nomis_config)
