#!/usr/bin/env python3
"""decode_denylist.py — turn the DISCLOSURE_DENYLIST_B64 secret into a private file (D-031).

The denylist reaches CI only as one line of base64, so the log masker holds a single long
string that no log line contains (a plain multi-line secret would mask each private term as
*** wherever repository text mentions it, and the public log would become an oracle for the
list). Publishing jobs decode it with this script into a file only the runner user can read,
and pass that file to check_disclosure.py with --denylist. Nothing derived from the value is
ever printed, not even in an error message, since that would undo what the base64 is for:

    python3 tools/publish/decode_denylist.py OUT_FILE   # reads $DISCLOSURE_DENYLIST_B64

Exit codes, each with the reason it is that code:

  0  The file is written with mode 0600, replacing whatever was there.
  3  The value is unset, empty or whitespace only. All three are read as "the secret is
     absent", because that is what a run without access to the secret sees; the caller
     decides whether absence is an error. pages.yml warns and skips its scan on a pull
     request and fails a deploy; wiki.yml, which only runs on a push or by hand, fails.
  1  The value is present but unusable, and nothing is written: it has whitespace inside it
     (so it is not one line of base64), it is not base64, it does not decode to UTF-8, it
     decodes to control characters other than tab, line feed and carriage return (so it is
     not a text file), or it holds no entries, only comments and blank lines. A present but
     broken secret is a setup mistake, never a reason to skip the scan.
  2  Not exactly one argument.

These rules are this script's own. The governance workflow's "Decode the private denylist"
step decodes the same secret with its own inline code, and differs in two places:

  - A value of whitespace only is "absent" here (exit 3) but "is blank." there, an error
    whether or not the check is required. So on a pull request whose secret is whitespace,
    pages.yml's scan warns and skips while governance fails.
  - A list of only comments and blank lines is refused here (exit 1, "no entries"). That step
    rejects only empty text, so it writes the file; the governance scans that then read it
    refuse it, because check_disclosure.parse_denylist raises on a list with no entries. The
    list is refused in both places, one step later in governance.

test_checks.py pins this script's side of both differences.

Standard library only.
"""

from __future__ import annotations

import base64
import binascii
import os
import sys

ENV = "DISCLOSURE_DENYLIST_B64"


def fail(why: str) -> int:
    print(f"decode_denylist: {ENV} {why} It must be the denylist file base64-encoded on one line.",
          file=sys.stderr)
    return 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: decode_denylist.py OUT_FILE", file=sys.stderr)
        return 2
    value = os.environ.get(ENV, "").strip()
    if not value:
        print(f"decode_denylist: {ENV} is not available to this run", file=sys.stderr)
        return 3
    if any(ch.isspace() for ch in value):
        return fail("has whitespace or a line break in it, so it is not one line of base64.")
    try:
        text = base64.b64decode(value, validate=True).decode("utf-8")
    except (binascii.Error, ValueError):
        return fail("is not base64 of UTF-8 text.")
    if any((ord(ch) < 32 and ch not in "\t\n\r") or ord(ch) == 127 for ch in text):
        return fail("decodes to bytes with control characters, so it is not a text file.")
    if not any(line.strip() and not line.lstrip().startswith("#") for line in text.splitlines()):
        return fail("decodes to a list with no entries.")
    out = argv[0]
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(out, 0o600)
    print("decode_denylist: denylist decoded to a private file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
