"""Altair S3 export utilities."""
import os
import tempfile
from uuid import uuid4

import boto3
from altair_saver import save

from sg_covid_impact import project_dir


def alt_to_s3(chart, bucket, key):
    """Save altair chart json to S3

    Args:
        chart (altair.vegalite.v4.api.Chart): Altair chart object to save
        bucket (str): Name of s3 bucket to save chart in
        key (str): Object key (i.e. path) within bucket to save chart to
    """
    s3 = boto3.client("s3")

    fname = f"{tempfile.gettempdir()}/{str(uuid4())}.json"
    save(chart, fname)
    with open(fname, "rb") as f:
        # Upload html, giving public read permissions,
        #  and with html content type metadata
        s3.upload_fileobj(
            f,
            bucket,
            key,
            ExtraArgs={"ContentType": "text/json", "ACL": "public-read"},
        )
    os.remove(fname)  # Cleanup temporary file


def export_chart(chart, key, bucket="scotland-figures"):
    """Export Altair `chart` to S3 as spec and locally as png.

    S3 goes to s3://`bucket`/`key`; local goes to
     `project_dir`/figures/`key`.
    """
    alt_to_s3(chart, "scotland-figures", f"{key}.json")
    chart.save(f"{project_dir}/figures/{key}.png")
