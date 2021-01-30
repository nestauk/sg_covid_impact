---
title: "Altair markdown example"
header-includes: |
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega@5"></script>
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega-lite@4.8.1"></script>
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega-embed@6"></script>
---

Include correct headers by having following at top of file
```
---
header-includes: |
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega@5"></script>
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega-lite@4.8.1"></script>
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega-embed@6"></script>
---
```

```
pandoc -s 1_introduction.md 2_literature.md 3_methodology.md\
 -f markdown\
 -o report.html\
 -F pandoc-crossref\
 --bibliography 'technicalreport.bib'\
 --filter ../../bin/altair_pandoc_filter.py\
 --metadata bucket="scotland-figures"\
 -C
```

## Current syntax style


This syntax...

```<div class=altair s3_path="test.json" static_path="png/bivariate_scatters.png" id="fig:pipeline2" width="500" height="20%">
can haz $ma^t_h$ again?
</div>
```

Yields...

<div class=altair s3_path="test.json" static_path="png/bivariate_scatters.png" id="fig:pipeline2" width="500" height="20%">
can haz $ma^t_h$?
</div>

### Parameters

* `s3_path` an S3 key in the bucket that was set in the command to pandoc (`--metadata bucket="<bucket-name>"`). Should contain the JSON spec for a vegalite visualisation.
* `static_path` a path to a static image that can be displayed in LaTeX, e.g. png.
* `width`, `height` - Altair doesn't seem to be able to do `%`.

## Making it more concise

I'm working on a more concise syntax:

`<altair s3_path="test.json" static_path="png/bivariate_scatters.png" caption="$E = mc^2$" id="fig:pipeline3" width="300"/>`

However it makes long captions hard to write, and ends up with a broken image symbol.
