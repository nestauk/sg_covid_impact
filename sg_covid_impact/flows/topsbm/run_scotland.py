# %%
"""Runs TopSBM flow on COVID notices from Scottish orgs."""
import json
import os
from pathlib import Path

from research_daps.flows.topsbm import topsbm

from sg_covid_impact import config
from sg_covid_impact.getters.glass import get_notice_tokens
from sg_covid_impact.queries.geography import get_notice_ids_for_scotland
from sg_covid_impact.utils.metaflow import update_model_config, execute_flow


def generate_documents() -> Path:
    """Generate notice tokens for organisations in Scotland."""
    scottish_notice_ids = get_notice_ids_for_scotland()

    docs = {k: v for k, v in get_notice_tokens().items() if k in scottish_notice_ids}

    path = Path("notice_documents_scotland.json").resolve()
    with open(path, "w") as f:
        json.dump(docs, f)

    return path


if __name__ == "__main__":
    os.environ[
        "METAFLOW_BATCH_CONTAINER_REGISTRY"
    ] = "195787726158.dkr.ecr.eu-west-2.amazonaws.com"

    config_ = config["flows"]["notice_topics"]["scotland"]
    params = config_["params"]

    filepath = generate_documents()

    cmd_params = {
        "--n-docs": str(params["n_docs"]),
        "--input-file": str(filepath),
    }
    flow_file = Path(topsbm.__file__).resolve()
    run_id = execute_flow(
        flow_file,
        cmd_params,
        metaflow_args={
            # "--with": "batch:memory=64000,image=metaflow-graph-tool",
        },
    )

    config_["run_id"] = run_id
    update_model_config(["flows", "notice_topics", "scotland"], config_)
