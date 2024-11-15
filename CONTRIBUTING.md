# Contributing Quick Reference

This document assumes you have some familiarity with Git, GitHub, and Python
virutalenvs. We are working on a more thorough guide about the different ways to
contribute with in depth explanations, which will be available soon.

These instructions will work with at least Bash and PowerShell, and should work
on other shells. On Windows, use PowerShell, not CMD.

You need Python and Git installed, as well as the [GitHub CLI]. Log in with
`gh auth login`. Choose and install an editor; we suggest [PyCharm] or
[VS Code].

[GitHub CLI]: https://cli.github.com/
[PyCharm]: https://www.jetbrains.com/pycharm/
[VS Code]: https://code.visualstudio.com/

## Set Up the Repository

Fork and clone the project's repository ("pallets/flask" for example). To work
on a bug or documentation fix, switch to the "stable" branch (if the project has
it), otherwise switch to the "main" branch. To update this target branch, pull
from "upstream". Create a work branch with a short descriptive name.

```
$ gh repo fork --clone pallets/flask
$ cd flask
$ git switch stable
$ git pull upstream
$ git switch -c short-descriptive-name
```

## Install Development Dependencies

Create a virtualenv and activate it. Install the dev dependencies, and the
project in editable mode. Install the pre-commit hooks.

Create a virtualenv (Mac and Linux):

```
$ python3 -m venv .venv
$ . .venv/bin/activate
```

Create a virtualenv (Windows):

```
> py -m venv .venv
> .\.venv\Scripts\activate
```

Install (all platforms):

```
$ pip install -r requirements/dev.txt && pip install -e .
$ pre-commit install --install-hooks
```

Any time you open a new terminal, you need to activate the virtualenv again. If
you've pulled from upstream recently, you can re-run the `pip` command above to
get the current dev dependencies.

## Run Tests

These are the essential test commands you can run while developing:

* `pytest` - Run the unit tests.
* `mypy` - Run the main type checker.
* `tox run -e docs` - Build the documentation.

These are some more specific commands if you need them:

* `tox parallel` - Run all test environments that will be run in CI, in
  parallel. Python versions that are not installed are skipped.
* `pre-commit` - Run the linter and formatter tools. Only runs against changed
  files that have been staged with `git add -u`. This will run automatically
  before each commit.
* `pre-commit run --all-files` - Run the pre-commit hooks against all files,
  including unchanged and unstaged.
* `tox run -e py3.11` - Run unit tests with a specific Python version. The
  version must be installed. `-e pypy` will run against PyPy.
* `pyright` - A second type checker.
* `tox run -e typing` - Run all typing checks. This includes `pyright` and its
  export check as well.
* `python -m http.server -b 127.0.0.1 -d docs/_build/html` - Serve the
  documentation.

## Create a Pull Request

Make your changes and commit them. Add tests that demonstrate that your code
works, and ensure all tests pass. Change documentation if needed to reflect your
change. Adding a changelog entry is optional, a maintainer will write one if
you're not sure how to. Add the entry to the end of the relevant section, match
the writing and formatting style of existing entries. Don't add an entry for
changes that only affect documentation or project internals.

Use the GitHub CLI to start creating your pull request. Specify the target
branch with `-B`. The "stable" branch is the target for bug and documentation
fixes, otherwise the target is "main".

```
$ gh pr create --web --base stable
```

CI will run after you create the PR. If CI fails, you can click to see the logs
and address those failures, pushing new commits. Once you feel your PR is ready,
click the "Ready for review" button. A maintainer will review and merge the PR
when they are available.
