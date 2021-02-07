#!/bin/bash
set -euo pipefail

cd $(dirname $0)/../reports/technical_report
pandoc -s 1_introduction.md 2_literature.md 3_methodology.md 4_results.md 5_conclusions.md\
 -f markdown\
 -o report.tex\
 --natbib -F pandoc-crossref\
 --bibliography 'technicalreport.bib'\
 --filter ../../bin/altair_pandoc_filter.py\
 --metadata figure_path="../../figures/scotland"
pdflatex report.tex
bibtex report || echo "Bibtex unsuccessful!"
pdflatex report.tex
pdflatex report.tex
