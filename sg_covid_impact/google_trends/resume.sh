#!/bin/bash

python gtab_flow_linear.py --no-pylint --package-suffixes .txt,.py resume --with batch:queue=job-queue-many-nesta-metaflow
