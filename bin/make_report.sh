#!/bin/bash
set -euo pipefail

cd $(dirname $0)/../reports/technical_report
pandoc -s 1_introduction.md 2_literature.md 3_methodology.md\
 -f markdown\
 -o report.tex\
 --natbib -F pandoc-crossref\
 --bibliography 'technicalreport.bib'
pdflatex report.tex
bibtex report || echo "Bibtex unsuccessful!"
pdflatex report.tex
pdflatex report.tex
