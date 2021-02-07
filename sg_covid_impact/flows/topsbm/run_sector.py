# %%
"""Runs TopSBM flow on COVID notices BY SIC section."""
import logging
import json
import os
from pathlib import Path

from research_daps.flows.topsbm import topsbm_grouped

import sg_covid_impact
from sg_covid_impact import config
from sg_covid_impact.getters.glass import get_notice_tokens
from sg_covid_impact.queries.sector import get_notice_ids_for_SIC_section
from sg_covid_impact.sic import section_code_lookup
from sg_covid_impact.utils.metaflow import update_model_config, execute_flow

MIN_SECTION_NDOCS = 100

logger = logging.getLogger(__name__)


def generate_documents(path: Path, match_threshold: int, max_rank: int) -> None:
    """Generate notice tokens broken up by SIC section."""
    valid_sections = list(set(section_code_lookup().values()))

    docs = []
    for section in valid_sections:
        logger.info(f"Getting notice tokens for SIC section {section}")
        section_notice_ids = get_notice_ids_for_SIC_section(
            section, match_threshold, max_rank
        )
        logging.info(f"{len(section_notice_ids)} notices for SIC section {section}")

        if len(section_notice_ids) < MIN_SECTION_NDOCS:
            logging.warning(f"Not enough documents, skipping SIC section {section}")
            continue

        section_docs = {
            k: v for k, v in get_notice_tokens().items() if k in section_notice_ids
        }
        docs.append([section, section_docs])

    with open(path, "w") as f:
        json.dump(docs, f)


if __name__ == "__main__":
    os.environ[
        "METAFLOW_BATCH_CONTAINER_REGISTRY"
    ] = "195787726158.dkr.ecr.eu-west-2.amazonaws.com"

    config_ = config["flows"]["notice_topics"]["section"]
    params = config_["params"]

    match_threshold = params["match_threshold"]
    max_rank = 5  # Multiple SIC per org to increase training data
    filepath = Path(
        f"notice_documents_SIC_section_{match_threshold}_{max_rank}.json"
    ).resolve()
    if not filepath.exists():
        generate_documents(filepath, match_threshold, max_rank)

    cmd_params = {
        "--n-docs": str(params["n_docs"]),
        "--input-file": str(filepath),
        "--max-workers": "6",
    }
    flow_file = Path(topsbm_grouped.__file__).resolve()
    run_id = execute_flow(
        flow_file,
        cmd_params,
        metaflow_args={
            "--with": "batch:memory=16000,image=metaflow-graph-tool",
        },
    )

    config_["run_id"] = run_id
    update_model_config(["flows", "notice_topics", "section"], config_)
