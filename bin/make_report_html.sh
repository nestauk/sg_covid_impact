#!/bin/bash
set -euo pipefail

cd $(dirname $0)/../reports/technical_report
pandoc -s 0_exec_summary.md\
 1_introduction.md\
 2_literature.md\
 3_methodology.md\
 4_results.md\
 5_conclusions.md\
 -f markdown\
 -o report.html\
 -F pandoc-crossref\
 --bibliography 'technicalreport.bib'\
 --filter ../../bin/altair_pandoc_filter.py\
 --metadata bucket="scotland-figures"\
 --resource-path="../../figures/.:."\
 --self-contained\
 --toc\
 -C
