# %%
"""Runs GlassHouseMatch flow."""
from pathlib import Path

from sg_covid_impact import config
from sg_covid_impact.flows.jacchammer import jacchammer
from sg_covid_impact.utils.metaflow import update_model_config, execute_flow


if __name__ == "__main__":
    config_ = config["flows"]["glass_house"]
    CH_flow_id = config["flows"]["companies_house"]["run_id"]
    glass_flow_id = config["flows"]["glass"]["run_id"]

    cmd_params = {
        "--test_mode": str(config_["params"]["test_mode"]),
        "--CH-flow-id": str(CH_flow_id),
        "--glass-flow-id": str(glass_flow_id),
    }
    flow_file = Path(jacchammer.__file__).resolve()
    run_id = execute_flow(
        flow_file,
        cmd_params,
        metaflow_args={
            "--package-suffixes": ".py,.txt",
        },
    )

    config_["run_id"] = run_id
    update_model_config(["flows", "glass_house"], config_)
