#!/bin/bash
set -euo pipefail

echo $(dirname $0)
cd $(dirname $0)/../reports/technical_report
pandoc -s 1_introduction.md 2_literature.md 3_methodology.md\
 -f markdown\
 -o report.html\
 -F pandoc-crossref\
 --bibliography 'technicalreport.bib'\
 --filter ../../bin/altair_pandoc_filter.py\
 --metadata bucket="scotland-figures"\
 -C