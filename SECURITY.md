# Security policy

Psyche is an open research project with one maintainer, the project lead, Cagan Caliskan
([@cagancaliskan](https://github.com/cagancaliskan)). This page says how to report a
vulnerability in what this repository publishes, what counts as one, and what to expect back.

## Reporting a vulnerability

Report it privately. Do not describe a vulnerability in a public issue, discussion or pull
request.

1. Open this repository's **Security** tab.
2. Choose **Report a vulnerability**. The direct link is
   <https://github.com/cagancaliskan/psyche/security/advisories/new>.
3. Fill in the form. The report is visible to the maintainer alone until an advisory is
   published.

The same form takes reports under the [Code of Conduct](CODE_OF_CONDUCT.md); leave any field that
only suits a vulnerability, such as severity or affected versions, empty.

GitHub private vulnerability reporting is the only channel. No email address is published for
this purpose.

A useful report says:

- what is affected: a page of the site, a file or a workflow, with the commit if you know it;
- how to reproduce it, as short as it can be made;
- what an attacker gains: what they can read, change or run;
- how you found it, and a fix if you have one in mind.

Please do not include secrets that belong to someone else. Please do not probe the deployed
site beyond reading it. The site is static pages, so a local build (see `website/README.md`)
reproduces anything that comes from its source.

## What is in scope

- **The documentation site.** The source in `website/` and the pages built from it, published
  at <https://cagancaliskan.github.io/psyche/>. For example: script injection through site code
  or staged content, a build step that ships something other than what the source says, a
  secret or a private path in the built output.
- **The Python substrate.** `src/psyche_*.py`. It uses the standard library only, opens no files
  or network connections and starts no processes. Its only calls into the operating system are
  read-only: clock readings, a load-average and a memory-use reading in
  `src/psyche_bodysensor.py`, and the random identifiers the standard library's `uuid` module
  draws. Its attack surface is small. Report it anyway if crafted input makes it execute code,
  read or write files, or use memory or time out of proportion to the input.
- **The cognitive-map package.** `cogmap/`, once its first release has been exported; the folder
  holds only a README until then. It changes only through a release export, so a report about it
  is handled the same way and the fix arrives as a new release.
- **The tooling and workflows.** `tools/`, `run_tests.py` and `.github/workflows/`. For example:
  a workflow that can be made to run untrusted input with write access or to expose a secret,
  an action reference that is not pinned to a commit, a permissions block wider than its job
  needs, a script that writes outside the repository.

## What is not in scope

- Vulnerabilities in software this project uses but does not maintain: Astro, Starlight, npm
  packages, GitHub Actions, GitHub Pages, GitHub itself. Report those to their maintainers. If
  this repository's configuration is what makes one exploitable, that part is in scope.
- Anything that needs the attacker to already control the maintainer's machine or GitHub
  account.
- Volumetric denial of service, social engineering and physical access.
- HTTP response headers set by GitHub Pages, which the project does not control.
- Scanner output with no demonstrated impact.
- A wrong claim, a stale number, a broken link or a rendering fault. These are bugs, not
  vulnerabilities: open a bug report through the issue form.

## What to expect

This is a volunteer project and the maintainer is one person. The aims below are aims, not
guarantees.

- **Acknowledgement** within 7 days of the report.
- **A first assessment** within 14 days: confirmed, not reproduced, or out of scope, with the
  reason.
- **A fix** on the default branch. Only the default branch is maintained: any future tagged
  release and the archived stage 1 record (the Zenodo DOI) are not patched in place.
- **Disclosure** coordinated with you. Once the fix is released, a GitHub security advisory
  describes the issue and credits you by name or handle, unless you prefer not to be named. The
  aim is to fix and disclose within 90 days of the report; if it will take longer, the report
  thread says why.

## No bounty

Psyche has no bug bounty and no budget for one. A confirmed report earns thanks and, if you
want it, credit in the advisory.

## Good faith

Research done in good faith, within this policy, is welcome: a private report, no access to
other people's data, no disruption of the site or the workflows.

Questions about how the repository handles security in general belong in
[GitHub Discussions](https://github.com/cagancaliskan/psyche/discussions), not in a report.
