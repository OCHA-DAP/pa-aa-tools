# aa-toolbox: Toolbox for anticipatory action

[![license](https://img.shields.io/github/license/OCHA-DAP/pa-aa-toolbox.svg)](https://github.com/OCHA-DAP/pa-aa-toolbx/blob/main/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

Currently under development

## Development

### Environment

To setup the development environment, please install all packages
from `requirements/requirements-dev.txt`:

```shell
pip install -r requirements/requirements-dev.txt
```

### Installation

To install in editable mode for development, execute:

```shell
pip install -e .
```

### Testing

To run the tests and view coverage, execute:

```shell
pytest --cov=aatoolbox
```

### Documentation

All public modules, classes and methods should be documented with
[numpy-style](https://numpydoc.readthedocs.io/en/latest/format.html)
docstrings, which are rendered into HTML using a pre-commit hook.
To view the docs, open up `docs/build/html/index.html` in your browser.

### pre-commit

All code is formatted according to
[black](https://github.com/psf/black) and
[flake8](https://flake8.pycqa.org/en/latest/) guidelines.
The repo is set-up to use
[pre-commit](https://github.com/pre-commit/pre-commit).
So please run `pre-commit install` the first time you are editing.
Thereafter all commits will be checked against black and flake8 guidelines

To check if your changes pass pre-commit without committing, run:

```shell
pre-commit run --all-files
```

### Packages

[`pip-tools`](https://github.com/jazzband/pip-tools)
is used for package management.

If you've introduced a new package to the source code (i.e. anywhere in `src/`),
please add it to the `install_requires` section of `setup.cfg` with any known
version constraints.
For adding packages for development, documentation, or tests,
add them to the relevant `.in` file in the `requirements` directory.
When you modify any of these lists, please try to keep them alphabetical!
Any changes to the `requirements*.txt` files will be generated with `pre-commit`.
For other functionality such as updating specific package versions, refer to the
`pip-tools` documentation.
