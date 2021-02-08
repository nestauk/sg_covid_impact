"""Runs WebsiteRegex flow to find twitter handles within Scottish business websites."""
import os
from pathlib import Path

import metaflow as mf
from research_daps.flows.website_regex import website_regex

from sg_covid_impact import config
from sg_covid_impact.getters.glass import get_organisation, get_address
from sg_covid_impact.utils.metaflow import update_model_config, execute_flow
from twitter_regex import TWITTER_REGEX


def scottish_urls() -> None:
    """Generate a list of Scottish business websites and save to `seed_urls.txt`."""
    orgs = get_organisation()
    addr = get_address()

    # TODO: get latest with tag production?
    scotland_laua_postcode_lookup = (
        mf.Run("NSPL/633")
        .data.nspl_data[["pcds", "laua"]]
        .loc[lambda x: x.laua.astype(str).str.contains("S")]
    )

    scottish_org_ids = (
        addr[["org_id", "postcode"]]
        .merge(scotland_laua_postcode_lookup, left_on="postcode", right_on="pcds")
        .org_id
    )
    scottish_business_urls = orgs[["org_id", "website"]].loc[
        lambda x: x.org_id.isin(scottish_org_ids)
    ]
    # ~45K URL's (~6% of total orgs with an address)
    # Population of scotland: ~5.5M
    # Population of UK: ~66M
    # => Scotland is ~8.3% of UK
    with open("seed_urls.txt", "w") as f:
        f.write("\n".join(scottish_business_urls.website.values.tolist()))


if __name__ == "__main__":
    # Generate seed URL's
    scottish_urls()

    os.environ[
        "METAFLOW_BATCH_CONTAINER_REGISTRY"
    ] = "195787726158.dkr.ecr.eu-west-2.amazonaws.com"

    config_ = config["flows"]["handle_finder"]
    params = config_["params"]

    cmd_params = {
        "--chunksize": str(params["chunksize"]),
        "--test_mode": str(params["test_mode"]),
        "--seed-url-file": str(Path(__file__).resolve().parents[0] / "seed_urls.txt"),
        "--regex": TWITTER_REGEX,
    }
    flow_file = Path(website_regex.__file__).resolve()
    run_id = execute_flow(
        flow_file,
        cmd_params,
        metaflow_args={
            "--package-suffixes": ".py,.txt",
            # "--metadata": "local",
            # "--datastore": "local",
            "--with": "batch:image=pyselenium",
            "--environment": "conda",
            # "--max-workers": "12",
        },
    )

    config_["run_id"] = run_id
    update_model_config(["flows", "handle_finder"], config_)
