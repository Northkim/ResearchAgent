# Development Environment Setup

- Date: 2026-07-20
- Status: Completed and verified
- Environment: `reagent-dev`
- Definition: `environment.yml`
- Platform verified: macOS arm64

## Environment created

The project now has a lightweight Conda environment declared as:

```yaml
name: reagent-dev
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pytest=8.4
```

Creation command:

```text
conda env create --file environment.yml
```

For a future update to an existing environment:

```text
conda env update --name reagent-dev --file environment.yml --prune
```

No FastAPI, SQLAlchemy, database driver, Redis client, LLM SDK, agent framework, or external validation library was added.

## Resolved environment details

- Conda: 25.5.1
- Prefix: `/Users/lifengguang/miniconda3/envs/reagent-dev`
- Python: 3.11.15
- pytest: 8.4.2
- Package source: conda-forge for every installed package

Direct project dependencies are only Python and pytest. Conda resolved these supporting packages:

- Python/test support: `colorama 0.4.6`, `exceptiongroup 1.3.1`, `iniconfig 2.3.0`, `packaging 26.2`, `pluggy 1.6.0`, `pygments 2.20.0`, `tomli 2.4.1`, `typing_extensions 4.16.0`
- Packaging tools supplied with the environment: `pip 26.1.2`, `setuptools 83.0.0`, `wheel 0.47.0`
- Runtime/system libraries supplied by Conda: `bzip2 1.0.8`, `ca-certificates 2026.6.17`, `libexpat 2.8.1`, `libffi 3.5.2`, `liblzma 5.8.3`, `libsqlite 3.53.3`, `libzlib 1.3.2`, `ncurses 6.6`, `openssl 3.6.3`, `readline 8.3`, `tk 8.6.13`, `tzdata 2026c`

## Verification results

Commands:

```text
conda run --no-capture-output -n reagent-dev python --version
conda run --no-capture-output -n reagent-dev pytest -q backend/domain/tests
conda run --no-capture-output -n reagent-dev python -m compileall -q backend
conda list -n reagent-dev
```

Results:

- Python reported `3.11.15`.
- pytest collected and passed all 5 existing domain tests in 0.58 seconds.
- Python compilation check completed with exit code 0 and no output.
- Installed package inspection confirmed all resolved packages came from conda-forge.

## Remaining actions

- Developers should create or update `reagent-dev` from `environment.yml` before running the next phase.
- Use `conda run -n reagent-dev ...` in automation until a CI environment is defined.
- Do not add a dependency unless production/test code imports or directly requires it.
- Workflow Engine implementation should initially continue using the standard library plus pytest only.
- A platform-specific lock file may be considered later if exact transitive builds must be identical across machines; it is not required for the current pure-domain phase.
