#!/bin/bash
set -euo pipefail

cd $(dirname $0)/../reports/technical_report
ln -s ../../figures/scotland . || echo ""
ln -s ../../figures/notice_length.png . || echo ""
pandoc -s 0_exec_summary.md\
 1_introduction.md\
 2_literature.md\
 3_methodology.md\
 4_results.md\
 5_conclusions.md\
 --metadata-file latex_metadata.yaml\
 -f markdown\
 -o report.tex\
 --bibliography 'technicalreport.bib'\
 --filter ../../bin/altair_pandoc_filter.py\
 --metadata figure_path="../../figures"\
 --natbib -F pandoc-crossref\
 --resource-path="../../figures/.:."\
 --variable fontfamily=arev\
 --variable urlcolor=blue
pdflatex report.tex
bibtex report || echo "Bibtex unsuccessful!"
pdflatex report.tex
pdflatex report.tex
\rm scotland notice_length.png
