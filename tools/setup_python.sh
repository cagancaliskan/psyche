#!/usr/bin/env bash
#
# setup_python.sh - install the CPython versions the project sweeps, with uv, and report
# whether each one resolves on PATH as python3.X and whether python3 itself is recent enough.
#
# Why it exists. CI runs every suite with all of these interpreters installed, and several of
# the tester suites (and tools/capture_run.py) look up python3.X on PATH for each version and
# compare the results across them. On a machine with fewer interpreters those suites report
# failures, or stop early, on a correct tree. This script gets a machine to the same set.
# uv installs only the versioned names (python3.X), never `python3`, and make runs `python3`,
# so the script also checks that `python3` is at least the lowest version of the list.
#
# What it does, in order:
#   1. stops with the documentation link when uv is not installed (it never installs uv,
#      and never downloads or pipes a script into a shell);
#   2. runs `uv python install` with the versions below (uv skips what it already has);
#   3. prints one line per version: python3.X and the path it resolves to, checked by running
#      it (a shim that is on PATH but does not run as that version is reported as such);
#   4. prints the line for `python3` itself;
#   5. if a version does not resolve or does not run, or python3 is missing or older than the
#      lowest version, says what to do about it and exits 1.
#
# Safe to run again. It needs no sudo, changes no shell profile and touches no network
# beyond what uv does itself. Usage: bash tools/setup_python.sh   (or: make setup)

set -euo pipefail

# The CPython minors to install, once. The same list is the CI matrix in
# .github/workflows/tests.yml and the set tools/capture_run.py sweeps;
# tools/publish/test_core.py fails when any of the three differs from this one.
VERSIONS=(3.10 3.11 3.12 3.13 3.14)

UV_DOCS_URL="https://docs.astral.sh/uv/getting-started/installation/"

if [ "$#" -gt 0 ]; then
  echo "usage: bash tools/setup_python.sh   (no arguments)" >&2
  exit 2
fi

# Prints "X.Y" for the interpreter at $1, and nothing when it does not run.
reports() {
  "$1" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true
}

if ! command -v uv >/dev/null 2>&1; then
  {
    echo "setup_python: uv is not installed, and uv is what installs the interpreters."
    echo "Install uv first; the official instructions are at"
    echo "  ${UV_DOCS_URL}"
    echo "then run this again. Nothing was changed."
  } >&2
  exit 1
fi

if ! uv python install "${VERSIONS[@]}"; then
  echo "setup_python: 'uv python install' failed; uv's message is above." >&2
  exit 1
fi

missing=""
broken=""
for v in "${VERSIONS[@]}"; do
  if found="$(command -v "python${v}" 2>/dev/null)"; then
    got="$(reports "${found}")"
    if [ "${got}" = "${v}" ]; then
      echo "python${v}  ${found}"
    else
      echo "python${v}  ${found}  does not run as ${v} (it reports: ${got:-an error})"
      broken="${broken} python${v}"
    fi
  else
    echo "python${v}  not found on PATH"
    missing="${missing} python${v}"
  fi
done

# python3 itself: make runs it, and the suites and tools need the lowest version of the list.
floor="${VERSIONS[0]}"
py3_note=""
if py3="$(command -v python3 2>/dev/null)"; then
  got="$(reports "${py3}")"
  new_enough=0
  case "${got}" in
    [0-9]*.[0-9]*)
      if [ "${got%%.*}" -gt "${floor%%.*}" ] ||
        { [ "${got%%.*}" -eq "${floor%%.*}" ] && [ "${got#*.}" -ge "${floor#*.}" ]; }; then
        new_enough=1
      fi
      ;;
  esac
  if [ "${new_enough}" -eq 1 ]; then
    echo "python3  ${py3}  reports ${got}"
  else
    echo "python3  ${py3}  reports ${got:-an error}, below the ${floor} the suites need"
    py3_note="older"
  fi
else
  echo "python3  not found on PATH"
  py3_note="missing"
fi

problems=0

if [ -n "${broken}" ]; then
  problems=1
  {
    echo ""
    echo "setup_python: found on PATH but not running as the right version:${broken}"
    echo "A version manager's shim can look like this when that version is not selected."
    echo "Put the directory of the real interpreter before it on PATH, then run this again."
  } >&2
fi

if [ -n "${missing}" ]; then
  problems=1
  bindir="$(uv python dir --bin 2>/dev/null || true)"
  if [ -z "${bindir}" ]; then
    bindir="${HOME:-}/.local/bin"
  fi
  {
    echo ""
    echo "setup_python: not found on PATH:${missing}"
    case ":${PATH}:" in
      *":${bindir}:"*)
        echo "uv's executable directory, ${bindir}, is already on PATH, so uv did not"
        echo "create the missing executables; read uv's messages above."
        ;;
      *)
        echo "uv puts the interpreters it installs in ${bindir}, which is not on PATH."
        echo "Add it to PATH in this shell and in your shell profile (for example ~/.zshrc"
        echo "or ~/.bashrc):"
        echo "  export PATH=\"${bindir}:\$PATH\""
        echo "then open a new terminal and run this again."
        ;;
    esac
  } >&2
fi

if [ -n "${py3_note}" ]; then
  problems=1
  {
    echo ""
    echo "setup_python: make runs python3, and python3 here is ${py3_note}: it needs to be ${floor} or newer."
    echo "uv installs only the versioned names above, never python3, so make one of them"
    echo "come first on PATH under that name. For example, with a directory that is ahead of"
    echo "the old python3 on PATH:"
    echo "  ln -s \"\$(command -v python${VERSIONS[${#VERSIONS[@]} - 1]})\" ~/.local/bin/python3"
    echo "then open a new terminal and run this again."
  } >&2
fi

if [ "${problems}" -ne 0 ]; then
  exit 1
fi

echo "setup_python: every interpreter resolves on PATH, and python3 reports ${got}."
