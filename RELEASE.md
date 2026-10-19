# Release / publish status

## PyPI: not published (owner action required)

Confirmed 2026-10-19: `https://pypi.org/pypi/launchmaxxing/json` returns 404
-- the package is not on PyPI. `pip install launchmaxxing` does not work
yet; only `pip install -e .` from a local clone (or a git URL) works today.
There is no PyPI account or API token for this project, and none should be
invented or worked around.

### Exactly what the owner needs to do

1. **Create a PyPI account** at <https://pypi.org/account/register/> (if one
   doesn't already exist for this project/org) and verify the email.
   Optional but recommended: also register on TestPyPI
   (<https://test.pypi.org/account/register/>) to do a dry-run upload first.
2. **Enable 2FA** on the PyPI account (PyPI requires 2FA for all accounts
   that publish packages).
3. **Reserve the project name** by doing a first manual upload, or claim it
   via PyPI's "pending publisher" flow (see trusted publishing below) --
   whichever happens first determines who owns the `launchmaxxing` name on
   PyPI.
4. **Generate an API token** at
   <https://pypi.org/manage/account/token/>, scoped to the `launchmaxxing`
   project once it exists (or scoped to the whole account for the very
   first upload, then narrow it to the project afterwards).
5. **Store the token as a GitHub Actions secret**, not in any file in this
   repo: Settings -> Secrets and variables -> Actions -> New repository
   secret, name `PYPI_API_TOKEN`, value = the token from step 4. This repo
   has no publish workflow wired up yet -- once the secret exists, a
   `publish.yml` workflow using `pypa/gh-action-pypi-publish` (or trusted
   publishing, see below) can be added to upload on a tagged release.
6. Alternative to API tokens: PyPI's **trusted publishing**
   (<https://docs.pypi.org/trusted-publishers/>) lets this exact GitHub
   repo + workflow publish without any stored secret at all, configured
   from the PyPI project settings page once the project exists there. This
   is the preferred long-term setup; it still requires the owner to create
   the PyPI account first (step 1) and link it to this repo from the PyPI
   UI.

Until an owner completes steps 1-4 (or 1 + 6), there is nothing to
automate here -- no token exists, so no publish workflow can run, and none
has been added. The README's "once published: `pip install launchmaxxing`"
line stays aspirational until this is done.
