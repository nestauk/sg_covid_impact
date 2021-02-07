#!/bin/bash
set -euo pipefail

cd $(dirname $0)/../reports/technical_report
# 1_introduction.md 2_literature.md 3_methodology.md\
pandoc -s twitter_analysis.md\
 -f markdown\
 -o report.html\
 -F pandoc-crossref\
 --bibliography 'technicalreport.bib'\
 --filter ../../bin/altair_pandoc_filter.py\
 --metadata bucket="scotland-figures"\
 -C
#  --template=clean_menu.html\
#  --toc\
