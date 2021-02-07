# %%
"""Runs TopSBM flow on COVID notices."""
import json
import os
import random
from pathlib import Path

from research_daps.flows.topsbm import topsbm

from sg_covid_impact import config
from sg_covid_impact.getters.glass import get_notice_tokens
from sg_covid_impact.utils.metaflow import update_model_config, execute_flow


def generate_documents(subsample_factor: float) -> Path:
    """Generate notice tokens."""
    docs = {
        k: v
        for k, v in get_notice_tokens().items()
        if random.random() < subsample_factor
    }

    path = Path("notice_documents_all.json").resolve()
    with open(path, "w") as f:
        json.dump(docs, f)

    return path


if __name__ == "__main__":

    os.environ[
        "METAFLOW_BATCH_CONTAINER_REGISTRY"
    ] = "195787726158.dkr.ecr.eu-west-2.amazonaws.com"

    config_ = config["flows"]["notice_topics"]["all"]
    params = config_["params"]

    filepath = generate_documents(params["subsample_factor"])

    cmd_params = {
        "--n-docs": str(params["n_docs"]),
        "--input-file": str(filepath),
    }
    flow_file = Path(topsbm.__file__).resolve()
    run_id = execute_flow(
        flow_file,
        cmd_params,
        metaflow_args={
            "--with": "batch:memory=64000,image=metaflow-graph-tool",
        },
    )

    config_["run_id"] = run_id
    update_model_config(["flows", "notice_topics", "all"], config_)
