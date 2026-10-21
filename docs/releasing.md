# Creating a GitHub Release with GitHub Actions

PyWPDoc GitHub Release publication is **not triggered by pushes, pull requests, CI success, or Pages deployment**. It is a separate, explicit decision. Publishing to PyPI remains a separate manual workflow.

## Before you release

1. Ensure the Windows Word/Hancom acceptance work applicable to the release was reviewed and recorded. For the published `0.44.0rc1`, see the [focused RC QA evidence](testing/native-qa-0440rc1-2026-10-18.md); fresh RC-specific PDF/pixel-layout QA was *not* included. **Do not treat that historical evidence as final approval for new version `0.44.0`.**
2. Merge all approved documentation, metadata and product changes into `main`.
3. Confirm that **PyWPDoc CI** ran from a `push` on **that exact `main` commit** and passed all ten jobs.
4. Confirm that the target tag does **not** exist and `pyproject.toml` contains exactly the requested package version.
5. Decide whether a second human approval is required. You can configure required reviewers for the `github-release` environment in **Settings → Environments → github-release**. Without that optional protection rule, entering `PUBLISH` and clicking `Run workflow` constitute the only release approval.

## Run a Release (after this workflow has merged to main)

Open **[Actions → Create PyWPDoc GitHub Release](https://github.com/rydolabs/PyWPDoc/actions/workflows/release.yml)**, select `main`, then fill in:

| Input | Example for first candidate |
| --- | --- |
| `release_tag` | `v0.44.0` (only after new version QA and approval) |
| `expected_sha` | The **full, current 40-character SHA of `main`**, after the final workflow change has merged and passed CI. Do **not** reuse an earlier SHA. |
| `confirm_release` | `PUBLISH` (case sensitive) |

Run the workflow. The verification job refuses to proceed if any of these differ: exact `main` SHA, requested package version, a successful `main` push CI, unused tag, or explicit confirmation. It builds the wheel and sdist, checks with `twine --strict`, and smoke-tests both DOCX/HWPX. After the optional environment-review step, the publish job **rechecks** `main`, the tag and SHA256 checksums, then creates a GitHub Release with wheel, sdist and `SHA256SUMS` assets.

For an `rcN` version it marks the result **Pre-release** and `Latest = false`. Stable versions are not marked as prereleases. It **never force-pushes or replaces an existing tag**. If a tag already exists, inspect it manually instead of rerunning the workflow.

## After the GitHub Release

- Verify the new [GitHub Releases page](https://github.com/rydolabs/PyWPDoc/releases), tag, release assets and their `SHA256SUMS` hashes.
- **PyPI is separate.** Only after reviewing the GitHub Release, go to [Actions → Publish PyWPDoc to PyPI](https://github.com/rydolabs/PyWPDoc/actions/workflows/publish.yml). Enter the published `release_tag`, run it, and approve the `pypi` environment when a required-reviewers rule is configured.
- PyPI Trusted Publishing still requires the correct project/pending-publisher configuration in PyPI. A GitHub Release is **not proof** that PyPI publishing is configured or complete.

The existing [Prepare PyWPDoc Release](https://github.com/rydolabs/PyWPDoc/actions/workflows/release-please.yml) only opens a release PR; it is not the Release creation workflow.

**Safety:** never use this procedure on a commit other than the final tested `main` revision. GitHub-hosted CI does not run Microsoft Word/Hancom COM tests.
