#!/bin/bash

aws s3 cp s3://nesta-production-config/research_daps.key . &&\
 git clone git@github.com:nestauk/research_daps.git &&\
 cd research_daps &&\
 git checkout 24_topsbm &&\
 git-crypt unlock ../research_daps.key &&\
 pip install -e . &&\
 pip install tornado>=6
