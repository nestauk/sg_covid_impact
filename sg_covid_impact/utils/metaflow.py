# %%
import pickle
import os
import logging
import yaml
from pathlib import Path
from typing import List
from itertools import chain
from subprocess import Popen, CalledProcessError
from shlex import quote
from filelock import FileLock

import toolz.curried as t
from dotenv import find_dotenv, load_dotenv
from metaflow import Flow, Run
from metaflow.client.core import MetaflowData

from sg_covid_impact import project_dir as PROJECT_DIR


logger = logging.getLogger(__file__)


def _get_temp_dir():
    """Find `temp_dir` env var or return None"""
    load_dotenv(find_dotenv())
    try:
        return os.environ["temp_dir"]
    except KeyError:
        return None


def cache_getter_fn(f):
    """Cache `f` output as pickle if `temp_dir` env var is set"""

    def inner(*args, **kwargs):
        temp_dir = _get_temp_dir()
        to_cache = True if temp_dir else False

        if not to_cache:
            return f(*args, **kwargs)
        else:
            cache_file = f.__qualname__
            cache_path = Path(temp_dir) / f.__module__
            cache_filepath = cache_path / cache_file

            if to_cache and not cache_path.exists():
                os.makedirs(cache_path, exist_ok=True)

            if cache_filepath.exists():
                with open(cache_filepath, "rb") as fp:
                    return pickle.load(fp)
            else:
                out = f(*args, **kwargs)
                with open(cache_filepath, "wb") as fp:
                    pickle.dump(out, fp)
                return out

    return inner


def flow_getter(flow: str, run_id=None) -> MetaflowData:
    """Return a function that fetches an artifact from a flow

    Args:
        flow (str): Metaflow flow name
        run_id (int, optional): Metaflow run id. If None, get the latest successful run.

    Returns:
        Callable[[str], object]
    """
    if run_id is None:
        run_id = Flow(flow).latest_successful_run.id
    return Run(f"{flow}/{run_id}").data


def execute_flow(flow_file: Path, params: dict) -> int:
    """Execute flow in `flow_file` with `params`

    Args:
        flow_file (`pathlib.Path`): File containing metaflow
        params (`dict`): Keys are flow parameter names (command-line notation,
             `--`), values are parameter values (as strings).

    Returns:
        `int` - run_id of flow

    Raises:
        `CalledProcessError`
    """
    run_id_file = flow_file.parents[0] / ".run_id"
    cmd = " ".join(
        [
            "python",
            str(flow_file),
            "--no-pylint",
            "run",
            "--run-id-file",
            str(run_id_file),
            # PARAMS
            *t.pipe(params.items(), chain.from_iterable, t.map(quote)),
        ]
    )
    logger.info(cmd)

    # RUN FLOW
    proc = Popen(
        cmd,
        shell=True,
    )
    while proc.poll():
        print("poll")
        print(proc.communicate())
    proc.wait()
    return_value = proc.returncode

    if return_value != 0:
        raise CalledProcessError(return_value, cmd)
    else:
        with open(run_id_file, "r") as f:
            run_id = int(f.read())
        return run_id


def update_model_config(key_path: List[str], value: object) -> None:
    """Update subsection of `model_config.yaml`

    Reads and writes under a file-lock so that multiple completing flows
    do not over-write one another.

    Args:
        key_path (`list`): Path in dictionary to update
        value (`object`): Value to put in `key_path`
    """
    fname = PROJECT_DIR / "sg_covid_impact" / "model_config.yaml"
    lock = FileLock(str(fname) + ".lock")
    with lock:
        # Read existing config
        with open(fname, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        # Update
        config_ = t.assoc_in(config, key_path, value)
        # Write
        with open(fname, "w") as f:
            f.write(yaml.dump(config_, default_flow_style=False))
