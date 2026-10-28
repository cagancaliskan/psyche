## Summary

<!-- What changes and why, in a few sentences. Link the issue or discussion it comes from. -->

## Checks

The commit gate and the CI jobs, from
[CONTRIBUTING.md](https://github.com/cagancaliskan/psyche/blob/main/CONTRIBUTING.md#what-a-pull-request-must-pass).
Tick what applies and say so under the list if something does not.

`make check` runs the commands down to the tool suites and `make test` runs the substrate's suites;
the plain commands are listed for a machine without make. `make test` exits 0 only with every
`python3.X` from 3.10 to 3.14 on your PATH (`make setup` installs them).

- [ ] `python3 tools/ledger_check.py --only C1,C3,C4,C5,C6` exits 0
- [ ] `python3 tools/publish/ci_c2.py` exits 0
- [ ] `python3 tools/publish/check_copy.py` exits 0
- [ ] `python3 tools/publish/render_plan.py --check` exits 0
- [ ] `python3 tools/publish/diagrams.py --check` exits 0
- [ ] The tool suites pass: `python3 tools/test_ledger.py`, `python3 -B tools/publish/test_core.py`
      and `python3 -B tools/publish/test_checks.py`
- [ ] The substrate's suites pass: `python3 run_tests.py`, for `src/` and `tests/`
- [ ] Site changes: `npm test` and `npm run build` pass in `website/`
- [ ] I read the change against rule 1 (never overclaim) and against
      [the disclosure policy](https://github.com/cagancaliskan/psyche/blob/main/docs/research/disclosure-policy.md);
      nothing in it comes from private material
- [ ] No typed counts: figures come from `tools/ledger.json`, and plan dates from
      `tools/research_plan.json` through `render_plan.py --write`, not from my own typing
- [ ] The commit holds only the files this change meant to touch
- [ ] No private identifier or wording appears in the commit messages, the branch name or a file
      name
