# Maintainer guide: PyWPDoc GitHub Release and PyPI (0.44.0rc1 review)

**Status: local release candidate; neither GitHub source nor PyPI artifacts have been published.**

1. Review source, test fixtures, screenshot provenance and third-party notices. The public GitHub repository is initially empty. Approve its first source push **separately**.
2. Trigger and verify `.github/workflows/ci.yml` on Linux / Windows across Python 3.10–3.13; the native Office/Hancom QA requires a licensed Windows host and the user's authorized Hancom Automation security module.
3. Confirm `pyproject.toml` version, changelog, API compatibility and intended tag. For example the release-candidate version `0.44.0rc1` corresponds to `v0.44.0rc1`; stable `0.44.0` corresponds to `v0.44.0`. Do not reuse already uploaded PyPI version numbers.
4. Review the release-please proposed PR if enabled, including pre-release numbering; merge **only with explicit maintainer approval**. Confirm the tag and published GitHub Release correspond to the commit with a green `PyWPDoc CI` run.
5. PyPI owner registered a **Pending Trusted Publisher**, owner `rydolabs`, repository `PyWPDoc`, workflow filename `publish.yml`, environment `pypi`; this will become active on the first successful OIDC publication. Do not issue a long-lived PyPI token. Ensure GitHub environment `pypi` has its intended Required reviewers restrictions (environment creation alone is not an approval gate).
6. With a separate **explicit PyPI publish approval**, manually start the `Publish PyWPDoc to PyPI` workflow and enter the approved GitHub Release tag. The `build` job validates published Release, matching tag/metadata, successful `PyWPDoc CI`, wheel/sdist build and `twine check`; only the `publish` job may request OIDC `id-token: write` and requires the `pypi` environment approval.
7. Confirm the uploaded artifact on `https://pypi.org/project/pywpdoc/`, then separately test a clean `pip install "pywpdoc[unified]==<version>"` and DOCX/HWPX create/open roundtrips.

**Never deploy in a unit test or CI test runner.** The approved release workflow is a distinct, manually initiated publishing action. GitHub Actions workflows have not been run on GitHub yet; local YAML parsing does not prove real remote behavior.

See `docs/maintainers/RELEASE_AUTOMATION_KO.md` for version automation caveats.
