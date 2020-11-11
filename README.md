sg_covid_impact
===============

Project with the Scottish Government to map the impact of Covid-19 in Scotland

# Stakeholders

This section provides an overview of where stakeholders from Scottish government can find relevant materials such as project plans, data quality reports etc.

# Contributors

## Setup

### Git hooks

Install the relevant git hooks by running `make git`.

See ["Approach to notebooks"](Approach to notebooks) for information on these hooks.

### AWS + Metaflow configuration

Much of the data pipeline is factored out of this repository and lives in Nesta's ["Research DAPS"](https://github.com/nestauk/research_daps).
Fetching the outputs of these pipelines is done via. the metaflow client API, and requires metaflow to be configured to use our AWS cloud stack. Please follow instructions [here](https://github.com/nestauk/research_daps#configuration) to do so.

## Code-style

Please run `make lint` to format your code to a common style, and to lint code with flake8.

## Approach to notebooks

Jupyter notebooks are great for exploration and presentation but cause problems for working collaboratively.

We use [Jupytext](https://jupytext.readthedocs.io/en/latest/) via. git hooks to automatically:
    - Convert notebooks to a `.py` format before committing
    - Convert `.py` "notebooks" back to notebooks when pulling/merging
This allows us to separate code from output data, facilitating easier re-factoring, testing, execution, and code review.
    
In addition, git hooks are configured to export notebooks as HTML, and push them to S3 when a git push is performed. This provides an automatic history of relevant notebooks without polluting git.

### A few things to be aware of:

- Autosaving: 
  - If Jupyter notebook autosaves the notebook while you are editing its jupytext'ed py counterpart then your changes will be over-written (see [jupytext docs](https://jupytext.readthedocs.io/en/latest/paired-notebooks.html#can-i-edit-a-notebook-simultaneously-in-jupyter-and-in-a-text-editor))
  - Likewise, if your editor autosaves the jupytext'ed py file then you risk losing changes in its notebook counterpart (see [jupytext docs](https://jupytext.readthedocs.io/en/latest/paired-notebooks.html#can-i-edit-a-notebook-simultaneously-in-jupyter-and-in-a-text-editor))
- `.ipynb` files are in `.gitignore`, if you force add them then they will be exported to HTML in the pre-commit hook but will then be unstaged and will not be committed - **always commit `.py` counterparts instead**

### Nitty gritty about the hooks

- Uses jupytext to pairs `.ipynb` files to a human readable `.py` counterpart (using the `percent` format)
- [pre-commit] Formats notebooks (and their `.py` counterparts) using `black`
- Exports `.ipynb` counterparts of committed `.py` files to HTML and stores them in `s3://nesta-notebook-db/<REPO_NAME>/<BRANCH_NAME>/<COMMIT_HASH>`
  - [pre-commit] These are stored in `.ipynb_export/`
  - [pre-push] These these are synced to S3 (push suggests an internet connection)
- [post-merge] (which occurs as part of a pull), convert jupytexted `.py` files to `.ipynb`
  - If a `.ipynb` notebook of that name already exists then it is backed up to `.ipynb_checkpoints` prefixed with the datetime of the backup

--------

<p><small>Project based on the <a target="_blank" href="https://github.com/nestauk/cookiecutter-data-science-nesta">Nesta cookiecutter data science project template</a>.</small></p>