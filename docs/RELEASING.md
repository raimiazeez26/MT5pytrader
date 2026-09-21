# Publishing MT5pytrader 2.0.0 to PyPI

This change prepares code and metadata only. It does not upload to either index.
Use the PyPI account that owns MT5pytrader. Keep credentials out of source control,
terminal command arguments, PR comments, and chat.

## 1. Merge and validate

Merge the implementation PR after CI passes. It includes PR #1's work, so PR #1
can be closed as superseded rather than merged separately. Review the migration
guide and complete [demo broker validation](DEMO_VALIDATION.md) before release.

Use a clean checkout of the merged commit and a supported Windows Python:

```powershell
git clone https://github.com/raimiazeez26/MT5pytrader.git MT5pytrader-release
cd MT5pytrader-release
git status --short
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m ruff check .
```

Confirm `pyproject.toml` and `MT5pytrader.__version__` both say `2.0.0`, update the
changelog's release date, and commit that change. Verify that version is still
unused on PyPI. If it has been used, choose a new version in both places and
update commands below. PyPI distribution filenames cannot be overwritten/reused.

## 2. Build and inspect

Use a new output directory so older distributions cannot be uploaded accidentally:

```powershell
.\.venv\Scripts\python.exe -m build --outdir dist/2.0.0
.\.venv\Scripts\python.exe -m twine check --strict dist/2.0.0/*
Get-FileHash dist/2.0.0/* -Algorithm SHA256
```

Expect `mt5pytrader-2.0.0-py3-none-any.whl` and
`mt5pytrader-2.0.0.tar.gz`. Inspect both for the package, version, README metadata,
and MIT LICENSE (the wheel includes it under `.dist-info/licenses/`). The wheel
is pure Python; its native MetaTrader5 dependency still limits actual trading to
supported Windows interpreters.

Install the local wheel in a fresh environment and run a no-connection smoke test:

```powershell
py -3.12 -m venv .smoke
.\.smoke\Scripts\python.exe -m pip install dist/2.0.0/mt5pytrader-2.0.0-py3-none-any.whl
.\.smoke\Scripts\python.exe -c "import MT5pytrader; print(MT5pytrader.__version__)"
```

Use this installed wheel for demo validation. Import alone does not initialize MT5.

## 3. Try TestPyPI first

TestPyPI has separate accounts/tokens from production PyPI. Register/login there
and create a token (project-scoped after the project exists). Twine's username is
`__token__`; enter the token only in its hidden password prompt. If your Twine
version presents token authentication directly, use that prompt.

```powershell
.\.venv\Scripts\python.exe -m twine upload --repository testpypi dist/2.0.0/*
```

If the name is already owned by someone else on TestPyPI, resolve ownership or
use local-wheel validation; do not rename the production distribution casually.
Test installing the staged release in another fresh environment. Install the
dependencies from production PyPI explicitly, then fetch only your package from
TestPyPI:

```powershell
py -3.12 -m venv .testpypi-smoke
.\.testpypi-smoke\Scripts\python.exe -m pip install pandas MetaTrader5
.\.testpypi-smoke\Scripts\python.exe -m pip install --index-url https://test.pypi.org/simple/ --no-deps "MT5pytrader==2.0.0"
.\.testpypi-smoke\Scripts\python.exe -c "from importlib.metadata import version; from MT5pytrader import Trader, TradeError; print(version('MT5pytrader'))"
```

This keeps dependency resolution separate from the test index. See the
[official TestPyPI guide](https://packaging.python.org/en/latest/guides/using-testpypi/).

## 4. Publish those validated artifacts

Create a **production PyPI** API token scoped to MT5pytrader. Upload the same
validated files without rebuilding:

```powershell
.\.venv\Scripts\python.exe -m twine upload dist/2.0.0/*
```

Enter production credentials through Twine's prompt. A 403 commonly indicates
incorrect token scope/account or wrong index; a duplicate-file error requires a
new version, not deleting/reusing an old filename. Do not rerun blindly after an
ambiguous upload failure; inspect the project's files first.

Check [the package page](https://pypi.org/project/MT5pytrader/) for the correct
version, rendered README, both artifacts, license and dependencies. Then install
from production PyPI into another fresh environment and confirm its metadata:

```powershell
py -3.12 -m venv .pypi-smoke
.\.pypi-smoke\Scripts\python.exe -m pip install --no-cache-dir "MT5pytrader==2.0.0"
.\.pypi-smoke\Scripts\python.exe -c "from importlib.metadata import version; import MT5pytrader; print(version('MT5pytrader'), MT5pytrader.__version__)"
git tag -a v2.0.0 -m "Release 2.0.0"
git push origin v2.0.0
```

Tag the exact clean commit used for the build and create a GitHub release with
the changelog, migration note and recorded demo-validation scope. Future fixes
should use 2.0.1 or another new version. If a bad release must be withdrawn,
consider PyPI yanking and publish a corrected version rather than replacing files.

## Optional later: Trusted Publishing

For subsequent automated releases, add a dedicated publishing workflow and
configure it under PyPI **Manage project → Publishing**. The configuration must
match owner `raimiazeez26`, repository `MT5pytrader`, the exact workflow filename,
and its GitHub environment. Publishing jobs need `id-token: write`; build/test
jobs do not. Use a protected environment to control release execution. This PR
only adds test/build CI, so no publisher workflow is registered or enabled by it.
See [PyPI's setup instructions](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
and the [Python packaging tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/).
