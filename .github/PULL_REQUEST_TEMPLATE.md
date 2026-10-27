## Summary

<!-- What changes and why, in a few sentences. Link the issue or discussion it comes from. -->

## Checks

The commit gate and the CI jobs, from
[CONTRIBUTING.md](https://github.com/cagancaliskan/psyche/blob/main/CONTRIBUTING.md). Tick what
applies and say so under the list if something does not.

- [ ] `python3 tools/ledger_check.py --only C1,C3,C4,C5,C6` exits 0
- [ ] `python3 tools/publish/ci_c2.py` exits 0
- [ ] `python3 tools/publish/check_copy.py` exits 0
- [ ] `python3 tools/publish/render_plan.py --check` exits 0
- [ ] Tests pass: `python3 run_tests.py` for `src/` and `tests/`, and `python3 tools/test_ledger.py`,
      `python3 tools/publish/test_core.py` and `python3 tools/publish/test_checks.py` for `tools/`
- [ ] Site changes: `npm test` and `npm run build` pass in `website/`
- [ ] I read the change against rule 1 (never overclaim) and against
      [the disclosure policy](https://github.com/cagancaliskan/psyche/blob/main/docs/research/disclosure-policy.md);
      nothing in it comes from private material
- [ ] No typed counts: figures come from `tools/ledger.json`, and plan dates from
      `tools/research_plan.json` through `render_plan.py --write`, not from my own typing
- [ ] The commit holds only the files this change meant to touch
- [ ] No private identifier or wording appears in the commit messages, the branch name or a file
      name
