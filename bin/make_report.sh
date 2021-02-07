#!/bin/bash
set -euo pipefail

cd $(dirname $0)/../reports/technical_report
# 1_introduction.md 2_literature.md 3_methodology.md\
pandoc -s twitter_analysis.md\
 -f markdown\
 -o report.tex\
 --bibliography 'technicalreport.bib'\
 --filter ../../bin/altair_pandoc_filter.py\
 --metadata figure_path="../../figures"\
 -F pandoc-crossref\
 --natbib
pdflatex report.tex
bibtex report || echo "Bibtex unsuccessful!"
pdflatex report.tex
pdflatex report.tex
