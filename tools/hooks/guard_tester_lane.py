#!/usr/bin/env python3
"""PreToolUse hook — keep the tester out of the code it certifies, and out of the ledger.

Four separate protections; the first two were learned the hard way.

1. FILES. The separation of duties is this project's primary evidence mechanism: "the role
   which writes a mechanism is never the role that certifies it." A tester that patches src/
   to make its own test pass voids the verification of everything it touched, and nothing in
   the transcript would show it.

2. CLAIM-BEARING TOOLS. capture_run.py and ledger_sync.py move the canonical assertion count.
   That count is a claim, and moving it is not the tester's to do — the same reason
   run_tests.py is off-limits. On 2026-07-25 a tester ran capture_run and produced a capture
   that omitted an unregistered suite; the ledger then recorded an under-reported total that
   was internally consistent and wrong. That was not a mistake inside a correct workflow, it
   was a tool in the wrong hands (D-016). Capture and sync belong to architect-pm, after the
   tester hands off.

3. D-031 PATHS AND GOVERNANCE. The thesis restructure added tooling and public surfaces that
   the tester verifies but does not own: the publishing tools, the docs site, CI, the thesis
   plan and the export-only thesis/ package. It also may not edit what binds it: every hook in
   tools/hooks/ (this guard included; the script is re-read on every call, so an editable
   guard could switch itself off), .claude/ (its own agent file carries the hook wiring, and
   settings.json the rest), and tools/ledger_check.py, which the commit gate runs.

4. SHELL WRITES. Items 1 and 3 hold for Write, Edit, MultiEdit and NotebookEdit, and a
   forbidden path is one shell command away from them, so a Bash command is read too. The
   tester keeps the shell for running and reading (cat, grep, sed -n, git diff, git show, cp
   from src/ to a scratch directory). A command is refused when it changes a forbidden path
   in a form read here: the target of a redirection (>, >>, >|, &>, >& file, <>); an
   argument of tee, touch, truncate, mkdir, rm, rmdir, unlink, shred, chmod, chown, chgrp,
   chflags, sudoedit or sudo -e, or of an in-place sed, perl or ruby; dd of=; the
   destination of cp, mv, ln, install, rsync, ditto or scp (also destination/name-of-source),
   and the source of mv; the paths given to git checkout, restore, rm, mv, clean and
   checkout-index (clean and checkout-index given no path act on the whole tree, read as
   "."; checkout-index paths carry its --prefix; checkout and restore with -p also count
   "."); a file a git command writes because an option names it (--output, format-patch -o,
   which otherwise writes into the current directory, archive -o, bundle create, config
   --file); the file time -o names; the directory git init or worktree add creates, and the
   one git worktree remove or move takes away; and the start paths of a find that deletes or
   runs a command.
   Removal, mode changes, the source of mv, those git paths and find also count a directory
   that holds a forbidden path, the repository root and any directory above it included (rm
   -rf tools, find . -delete, git checkout -- ., git clean -fdx). Quoting is honoured, so a
   quoted ">" is text, and here-document bodies are skipped. Commands are read the same way
   after ; && || | and newlines, inside $( ) and backticks (also within double quotes), in
   sh/bash/zsh -c, eval and find -exec, and behind the wrappers sudo, doas, env, command,
   builtin, exec, nohup, nice, time, timeout, stdbuf, caffeinate, unbuffer, setsid and arch.
   A GNU tool that MacPorts or Homebrew installs under a g prefix is read as the tool it
   names (_GNU_PREFIXED) when that is one of tee through chflags or cp through scp above,
   dd, sed, find, xargs, patch, or the wrapper timeout, env, nice, stdbuf, nohup or time:
   grm is rm, gtimeout is timeout, and git is never read as a g before "it". A wrapper
   is read past its options and their values, so in sudo -u me rm the command is
   rm, not me; the word after an option missing from the wrapper's table (_PREFIX_OPTIONS)
   is read both as that option's value and as the command, and the targets of every reading
   count. A long option written out in full is that option, as getopt_long reads it (sudo
   --login is a flag, though --login-class takes a value). After "--" the words are read with
   options off, assignments and numbers still passed over (timeout -- 10 rm), and with
   options on as well, for a wrapper that does not honour "--". timeout's first operand is
   its DURATION in any spelling strtod reads (10s, 1e3, inf), and it is read as the command
   as well. The string env -S splits is read as the command it becomes.
   Every directory named by cd, pushd, git -C, env -C or sudo -D is tried as a base, and
   globs and environment variables of the hook's own environment ($CLAUDE_PROJECT_DIR,
   $HOME) are expanded.
   Refused outright, because they change paths this hook cannot see: patch; git apply and am
   (a --check, --stat, --numstat or --summary report without --apply excepted); git reset
   --hard, --merge or --keep; git merge, pull, rebase, cherry-pick, revert and read-tree
   (which also writes an index to any file); git checkout -f, git switch -f,
   --discard-changes or --orphan; a path list given by --pathspec-from-file; git stash,
   bisect, sparse-checkout and submodule except their read-only forms; a git worktree action
   other than add, remove, move (read above), list, prune, lock, unlock and repair; and every
   git subcommand this hook does not read (_GIT_READS and the ones above), an alias among
   them. git's long options are matched as git abbreviates them (--har is --hard). A command
   run by xargs gets the words xargs reads from its input, appended or put where its
   replace string stands; a command that would change one of them is refused, since its
   path is unseen, and so is a command whose name comes from that input (xargs env, xargs
   -I{} {}); xargs given no command runs echo. Also refused: a command nested more than
   five levels deep (_MAX_DEPTH) through sh -c, eval and find -exec, and through a $( ) or a
   backtick pair that sits inside a quoted word (escaped quotes within it, say), which the
   lexer reads one level deeper, because this hook stops reading there; it is refused even
   when it is harmless. The usual spelling, a "$( )" inside a double-quoted "$( )", is read
   flat: the quoted word ends at the inner quote and the "$(" after it is an operator, so
   every level of it is read as a command of its own, never counted as nesting and never
   refused for depth. Backticks are never read nested: one backtick substitution goes
   inside another only with its backticks escaped by a backslash, which the lexer reads as
   text, so a command whose text holds an escaped backtick outside single quotes (a comment
   and a here-document body aside) is refused outright, as "a nested backtick substitution
   this hook does not read", even a harmless one such as an escaped backtick printed inside
   double quotes. A backtick inside single quotes is text, and an unnested pair (echo
   `date`) is read as above. Refused as "a command too long for this hook to read", however
   harmless, because Claude Code lets a call through when its hook runs out of time: a
   command longer than 4096 characters (_MAX_COMMAND), one whose reading takes more than
   _MAX_WORK steps (wrapper after wrapper behind an option this hook does not know, find
   -exec inside find -exec, cd after cd, globs that scan many directories, whether or not
   they match), and one still being read after _MAX_SECONDS seconds, the bound for work the
   step count weighs too lightly (judging many deep paths) or does not count at all.
   Not seen, each pinned as an asserted negative in tools/publish/test_hooks.py: a write made
   from inside a program (python -c, or a script it runs) or by a command git itself runs (a
   hook, a command set with git -c, the pager git grep -O names), a path the shell assembles
   at run time (a shell variable, brace expansion, a name xargs passes into a nested shell as
   "$@" or as its replace string), a command behind a wrapper not named above (flock,
   watch, script, su -c), and a branch switch (git checkout <branch>, git switch <branch>),
   which rewrites the working tree. This is a backstop for the common forms, not a sandbox.

Wired into the tester agent's frontmatter, so it applies to that lane only.
Exit 2 blocks the tool call and shows stderr to Claude.

Which file is the target: the path as the tool resolves it. It is made absolute against the
session cwd, a leading "~" is read as the home directory, ".." is removed lexically, and then
symlinks are resolved: realpath(normpath(path)), which is the file Claude Code writes. The
spelling that resolves symlinks first, realpath(path), and the literal "~" are judged as well,
and the target is blocked if any of them is forbidden, so <repo>/tests/link/../../src/a.py is
src/a.py wherever the link points.

Which directory is the repository: every ancestor of the target that holds tools/ledger.json,
and the target is blocked if it is forbidden relative to ANY of them, so a stray
tools/ledger.json planted under tools/ cannot shorten tools/thesis_plan.json to an allowed
name. A path inside a nested worktree, .claude/worktrees/<name>/..., is judged as the same
path of that checkout, whether or not the checkout holds its own ledger: a tester working in
a worktree is held to the same lane. Only when no ancestor holds tools/ledger.json does it
fall back to the longest of CLAUDE_PROJECT_DIR and the payload cwd that contains the target.

stdin is read as bytes and decoded as UTF-8, whatever PYTHONIOENCODING or the locale say: this
checkout's path is not ASCII, and a payload that cannot be decoded would let every write
through.

Paths are compared after Unicode NFC normalisation and case folding. This checkout lives
under a directory the filesystem stores decomposed (NFD), while a path typed into a tool
call is usually composed (NFC); compared raw, the two never match and the guard would
silently allow every write.
"""

from __future__ import annotations

import collections
import fnmatch
import json
import os
import re
import signal
import sys
import unicodedata

FORBIDDEN_PREFIXES = (
    "src/",
    "thesis/",               # export-only (D-031): no agent edits it
    "tools/publish/",        # builder lane (D-031)
    "tools/hooks/",          # builder lane (D-031); every hook, this guard included
    "website/",              # builder lane (D-031)
    ".github/",              # builder lane (D-031)
    ".claude/",              # agent files (this lane's hook wiring), settings, skills
)
FORBIDDEN_EXACT = (
    "run_tests.py",          # controls what the canonical count includes
    "CLAUDE.md",
    "tools/ledger.json",     # the claim-bearing fact base
    "docs/TEST_OUTPUT.txt",  # the capture the ledger is generated from
    "tools/thesis_plan.json",  # the only source of thesis dates (D-031)
    "tools/ledger_check.py",   # the staleness check the commit gate runs
    "tools/capture_run.py",    # claim-bearing tools: not run (below), and not edited either
    "tools/ledger_sync.py",
)
WORKTREES = ".claude/worktrees/"
FORBIDDEN_TOOLS = ("capture_run.py", "ledger_sync.py")

HANDBACK = (
    "If you have found a defect: report it precisely — the exact failing input, expected vs\n"
    "actual, and your best read on the root cause — and hand back. Fixing or re-labelling the\n"
    "thing you are testing reintroduces exactly the circularity this project exists to avoid.\n"
)


def block(msg: str) -> int:
    sys.stderr.write(f"LANE VIOLATION — blocked.\n\nYou are in the tester lane. {msg}\n")
    return 2


def _nfc(p: str) -> str:
    return unicodedata.normalize("NFC", p)


def _marked(d: str) -> bool:
    return os.path.isfile(os.path.join(d, "tools", "ledger.json"))


def resolve_target(target: str, base: str) -> list:
    """Every absolute spelling of the target to judge (see the module docstring)."""
    spellings = [os.path.expanduser(target)] if target.startswith("~") else []
    spellings.append(target)
    out = []
    for t in spellings:
        p = t if os.path.isabs(t) else os.path.join(base, t)
        for c in (os.path.realpath(os.path.normpath(p)), os.path.realpath(p)):
            if c not in out:
                out.append(c)
    return out


def repo_relatives(target: str, cwd: str) -> list:
    """Every repository-relative spelling of the target (see the module docstring)."""
    project = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    base = cwd or project or os.getcwd()
    rels = []
    for raw in resolve_target(target, base):
        rels += [r for r in _relatives_of(raw, project, cwd) if r not in rels]
    return rels


def _relatives_of(raw: str, project: str, cwd: str) -> list:
    tn = _nfc(raw)

    roots = []
    d = os.path.dirname(raw)
    while True:
        if _marked(d):
            roots.append(d)
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    if not roots:
        bases = [b for b in (project, cwd) if b]
        inside = [b for b in bases
                  if tn.startswith(_nfc(os.path.realpath(b)).rstrip("/") + "/")]
        if inside:
            roots = [max(inside, key=lambda b: len(_nfc(os.path.realpath(b))))]

    rels = []
    for r in roots:
        rn = _nfc(os.path.realpath(r)).rstrip("/")
        if tn.startswith(rn + "/"):
            rels.append(tn[len(rn) + 1:])
    return rels


def forbidden(rel: str) -> bool:
    key = rel.casefold()
    if key.startswith(WORKTREES):
        # a nested worktree is a checkout of this repository: judge the path inside it
        parts = rel[len(WORKTREES):].split("/", 1)
        return len(parts) < 2 or not parts[1] or forbidden(parts[1])
    return (key in (e.casefold() for e in FORBIDDEN_EXACT)
            or any(key.startswith(p.casefold()) for p in FORBIDDEN_PREFIXES))


# ── shell writes (item 4 of the module docstring) ────────────────────────────

# Longest first, so ">>" is read before ">".
_OPERATORS = ("&>>", "<<<", "<<-", ">>", "&>", ">|", ">&", "<&", "<>", "<<", "&&", "||", "|&",
              ";;", "$(", "<(", ">(", ";", "&", "|", "(", ")", "<", ">", "\n", "`")
_OPERATOR_STARTS = frozenset(o[0] for o in _OPERATORS)
_WRITE_REDIRECTS = (">", ">>", ">|", "&>", "&>>", "<>")
_READ_REDIRECTS = ("<", "<<", "<<-", "<<<", "<&")
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Words that run the command after them (with their own options). xargs is read on its own.
_PREFIXES = {"sudo", "doas", "env", "command", "builtin", "exec", "nohup", "nice", "time",
             "timeout", "stdbuf", "caffeinate", "unbuffer", "setsid", "arch", "then", "do",
             "else", "elif", "if", "while", "until", "!", "{", "}"}
# The options of a wrapper, from its GNU and BSD manuals: (short flags, short options that
# take a value, long flags, long options that take a value). The table tells a value from
# the command: in sudo -u me rm, me is -u's value and rm the command. It need not be
# complete. An option missing from it may or may not take the next word, so _prefix_starts
# reads that word both ways; a wrong guess here would be the only way to skip the command.
_PREFIX_OPTIONS = {
    "sudo": ("ABbEeHiKklNnPSsVv", "aCcDghpRrTtUu",
             ("askpass", "bell", "background", "preserve-env", "edit", "help", "set-home",
              "login", "remove-timestamp", "reset-timestamp", "list", "no-update",
              "non-interactive", "preserve-groups", "stdin", "shell", "version", "validate"),
             ("auth-type", "close-from", "chdir", "group", "host", "login-class", "prompt",
              "chroot", "role", "type", "command-timeout", "other-user", "user")),
    "doas": ("Lns", "Cu", (), ()),
    "env": ("0iv", "aCLPSUu",
            ("ignore-environment", "null", "debug", "list-signal-handling", "block-signal",
             "default-signal", "ignore-signal", "help", "version"),
            ("argv0", "chdir", "split-string", "unset")),
    "timeout": ("fpv", "ks", ("foreground", "preserve-status", "verbose", "help", "version"),
                ("kill-after", "signal")),
    "nice": ("", "n", ("help", "version"), ("adjustment",)),
    "stdbuf": ("", "eio", ("help", "version"), ("error", "input", "output")),
    "exec": ("cl", "a", (), ()),
    "command": ("pVv", "", (), ()),
    "time": ("ahlpqVv", "fo", ("append", "portability", "quiet", "verbose", "help", "version"),
             ("format", "output")),
    "caffeinate": ("dimsu", "tw", (), ()),
    "unbuffer": ("p", "", (), ()),
    "setsid": ("cfw", "", ("ctty", "fork", "wait", "help", "version"), ()),
}
# Wrapper options whose value does more than set a mode: the directory the command runs in
# (env -C, sudo -D), the string env splits into the command (env -S), the file time writes.
_PREFIX_EFFECTS = {"env": {"C": "chdir", "chdir": "chdir", "S": "split", "split-string": "split"},
                   "sudo": {"D": "chdir", "chdir": "chdir"},
                   "time": {"o": "write", "output": "write"}}
# A number before the command (an adjustment, nice 5), passed over. timeout's DURATION is not
# read by this pattern: strtod takes spellings it does not match (inf, 1e3), so _prefix_starts
# passes over timeout's first operand whatever it is.
_NUMBER_RE = re.compile(r"^[0-9.]+[smhd]?$")
# xargs options that take the next word as their value (GNU and BSD).
_XARGS_VALUED = {"-I", "-J", "-L", "-n", "-P", "-s", "-E", "-d", "-a", "-R", "-S",
                 "--max-args", "--max-procs", "--delimiter", "--arg-file", "--max-chars",
                 "--process-slot-var"}
# Stands for the words xargs appends from its input; a NUL never reaches a shell word.
_APPENDED = "\0"
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
_REMOVES = {"rm", "rmdir", "unlink", "shred", "srm", "chmod", "chown", "chgrp", "chflags"}
_WRITES = {"tee", "touch", "truncate", "mkdir"}
_COPIES = {"cp", "mv", "ln", "install", "rsync", "ditto", "scp"}
_IN_PLACE = {"sed": re.compile(r"^(-[nrsEuzl0-9]*i|--in-place)"),
             "perl": re.compile(r"^-[aclnpsStTuUwWX0-9]*i"),
             "ruby": re.compile(r"^-[acdlnpsSvwWx0-9]*i")}
# The tools read here that a package manager (MacPorts, Homebrew) installs under a g prefix,
# GNU's spelling beside the system's own: grm is rm, gtimeout is timeout. git is not g + it.
_GNU_PREFIXED = frozenset(_REMOVES | _WRITES | _COPIES
                          | {"dd", "sed", "find", "xargs", "patch",
                             "timeout", "env", "nice", "stdbuf", "nohup", "time"})
_FIND_ACTIONS = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0",
                 "-fprintf", "-fls"}
_MAX_DEPTH = 5
_MAX_GLOB = 500
# Past _MAX_DEPTH this hook stops reading, so it cannot tell what the command changes: it is
# refused (fail closed), never let through unread.
_TOO_DEEP = (None, False, f"a command nested more than {_MAX_DEPTH} deep")
# A backtick substitution nested in another is written with escaped backticks, which _lex
# reads as plain text; rather than read them, a command that holds one is refused.
_NESTED_BACKTICK = "a nested backtick substitution this hook does not read"
# Claude Code kills a hook that runs out of time and lets the call through, so a command this
# hook cannot read quickly is refused instead: one longer than _MAX_COMMAND characters, one
# whose reading takes more than _MAX_WORK steps (_spend says what a step is), and, as a
# backstop for work no step counts, one still being read after _MAX_SECONDS (shell_hit).
_MAX_COMMAND = 4096
_MAX_WORK = 50_000
_MAX_SECONDS = 5
_JUDGE_STEPS = 10   # judging one path against the repository walks the filesystem
_TOO_LONG = "a command too long for this hook to read"
_GLOB_MAGIC = re.compile(r"[*?[]")      # glob.has_magic
# What to do instead, for a refusal that is about the form of a command, not its target.
_ADVICE = {
    _NESTED_BACKTICK: "Write the inner command as $( ), or put a literal backtick inside\n"
                      "single quotes.\n\n",
    _TOO_LONG: "Split it into shorter commands, and write a long file with the Write tool.\n\n",
}


class _TooLong(Exception):
    """Reading the command has gone past a limit: _MAX_WORK steps (see _spend) or
    _MAX_SECONDS (see shell_hit). Its text names the limit."""


_work_done = 0      # the steps spent on the command being read; shell_hit resets it


def _spend(steps: int) -> None:
    """Count `steps` of reading work, and stop reading (raise _TooLong) past _MAX_WORK.

    A step is a reading popped in _command_targets, a word read by one live reading in
    _prefix_starts, a word of a word list made for xargs or env -S, a word of a command find
    -exec runs, a word lexed, a base tried by cd and the like, a directory entry a glob
    reads and a name it looks up (_glob: whether or not either matches, so a pattern that
    scans many directories and matches nothing is paid for), and (_JUDGE_STEPS each) a path
    judged against the repository in shell_hit. Measured on the development machine, most
    steps took from about 1 to 25 microseconds, so for ordinary commands the budget ends
    reading in well under 2 s. Judging a path is charged a flat _JUDGE_STEPS although its
    real cost grows with the path's depth (every component is resolved), so a command that
    sends many deep paths to be judged can stay under the budget for several seconds; for
    that work the _MAX_SECONDS timer is the bound that applies. Either way reading ends
    within about _MAX_SECONDS, far inside the 15 s timeout the tester's agent file sets."""
    global _work_done
    _work_done += steps
    if _work_done > _MAX_WORK:
        raise _TooLong(f"over {_MAX_WORK} steps of reading")


def _out_of_time(signum, frame) -> None:
    raise _TooLong(f"over {_MAX_SECONDS:g} seconds of reading")

# git, by what a subcommand does to the working tree (item 4 of the module docstring).
# The paths given to these are read as rm's are; clean and checkout-index are read below.
_GIT_PATHS = {"checkout", "restore", "rm", "mv"}
# These leave the working tree alone, apart from a file an option names (_git_targets).
_GIT_READS = frozenset("""
    add annotate blame branch cat-file check-attr check-ignore check-mailmap check-ref-format
    cherry column commit commit-graph commit-tree count-objects describe diff diff-files
    diff-index diff-tree fetch for-each-ref fsck gc get-tar-commit-id grep hash-object help
    log ls-files ls-remote ls-tree merge-base merge-tree mktag mktree name-rev notes pack-refs
    prune push range-diff reflog remote repack replace rev-list rev-parse shortlog show
    show-branch show-index show-ref status stripspace symbolic-ref tag update-index update-ref
    var verify-commit verify-pack verify-tag version whatchanged write-tree
""".split())
# Refused outright: each rewrites working-tree paths this hook cannot name. read-tree also
# writes an index to any file (--index-output).
_GIT_REFUSED = {"merge", "pull", "rebase", "cherry-pick", "revert", "read-tree"}
# Refused except in these read-only forms (the first operand; "" is none given).
_GIT_READ_FORMS = {"stash": {"list", "show"},
                   "bisect": {"", "log", "view", "visualize", "terms", "help"},
                   "sparse-checkout": {"list", "check-rules"},
                   "submodule": {"", "status", "summary"}}
# Short options of format-patch (its own and the diff options) that take the rest of their
# cluster as a value, so an "o" after one of them is not -o. archive has none.
_FORMAT_PATCH_VALUED = "vSGUOIXlMCB"

# A target: (path, or None when the command can change paths no one can name; whether a
# directory that holds a forbidden path counts; what the command does).
Target = tuple


def _lex(cmd: str, nested: "list | None" = None) -> list:
    """The words and operators of a shell command, as (text, is operator).

    Quotes and backslashes are removed from words, so a quoted ">" is a word, not a
    redirection. A file-descriptor number written against a redirection ("2>") is dropped,
    a comment is skipped, and so is the body of a here-document. An escaped backtick met
    outside single quotes (unquoted or within double quotes), the spelling of a backtick
    substitution nested in another, is recorded in `nested` when it is given."""
    out = []
    buf = []
    state = {"word": False, "delim": None}
    heredocs = []
    i, n = 0, len(cmd)

    def flush():
        if state["word"]:
            text = "".join(buf)
            out.append((text, False))
            if state["delim"] is not None:
                heredocs.append((text, state["delim"]))
                state["delim"] = None
        buf.clear()
        state["word"] = False

    while i < n:
        c = cmd[i]
        if c in " \t\r":
            flush()
            i += 1
        elif c == "\\":
            if i + 1 < n and cmd[i + 1] != "\n":
                buf.append(cmd[i + 1])
                state["word"] = True
                if cmd[i + 1] == "`" and nested is not None:
                    nested.append(i)
            i += 2
        elif c == "'":
            j = cmd.find("'", i + 1)
            j = n if j < 0 else j
            buf.append(cmd[i + 1:j])
            state["word"] = True
            i = j + 1
        elif c == '"':
            j = i + 1
            while j < n and cmd[j] != '"':
                if cmd[j] == "\\" and j + 1 < n and cmd[j + 1] in '"\\$`\n':
                    if cmd[j + 1] != "\n":
                        buf.append(cmd[j + 1])
                    if cmd[j + 1] == "`" and nested is not None:
                        nested.append(j)
                    j += 2
                else:
                    buf.append(cmd[j])
                    j += 1
            state["word"] = True
            i = j + 1
        elif c == "#" and not state["word"]:
            j = cmd.find("\n", i)
            i = n if j < 0 else j
        else:
            op = (next((o for o in _OPERATORS if cmd.startswith(o, i)), None)
                  if c in _OPERATOR_STARTS else None)
            if op is None:
                buf.append(c)
                state["word"] = True
                i += 1
                continue
            if (state["word"] and "".join(buf).isdigit()
                    and op in _WRITE_REDIRECTS + _READ_REDIRECTS + (">&",)):
                buf.clear()
                state["word"] = False
            flush()
            out.append((op, True))
            i += len(op)
            if op in ("<<", "<<-"):
                state["delim"] = op
            elif op == "\n":
                for delim, kind in heredocs:
                    while i < n:
                        j = cmd.find("\n", i)
                        line = cmd[i:n if j < 0 else j]
                        i = n if j < 0 else j + 1
                        if (line.lstrip("\t") if kind == "<<-" else line) == delim:
                            break
                heredocs.clear()
    flush()
    return out


def _simple_commands(lexed: list) -> list:
    """(words, redirection targets written) of each simple command."""
    cmds = []
    words, writes = [], []
    i = 0
    while i < len(lexed):
        text, is_op = lexed[i]
        nxt = lexed[i + 1][0] if i + 1 < len(lexed) and not lexed[i + 1][1] else None
        if not is_op:
            words.append(text)
            i += 1
            continue
        if text in _WRITE_REDIRECTS or text == ">&":
            if nxt is not None and not (text == ">&" and (nxt.isdigit() or nxt == "-")):
                writes.append(nxt)
            i += 2 if nxt is not None else 1
            continue
        if text in _READ_REDIRECTS:
            i += 2 if nxt is not None else 1
            continue
        if words or writes:
            cmds.append((words, writes))
        words, writes = [], []
        i += 1
    if words or writes:
        cmds.append((words, writes))
    return cmds


def _split_args(args: list) -> tuple:
    """(options, operands); every word after "--" is an operand."""
    opts, plain = [], []
    for k, a in enumerate(args):
        if a == "--":
            return opts, plain + list(args[k + 1:])
        (opts if a.startswith("-") and a != "-" else plain).append(a)
    return opts, plain


def _substituted(word: str) -> list:
    """The commands inside $( ) and backticks within one word (a double-quoted one, say)."""
    out = []
    at = word.find("$(")
    if at >= 0:
        out.append(word[at + 2:])
    parts = word.split("`")
    out += parts[1::2]
    return out


# ── git options, read as git's own option parser reads them ─────────────────

def _short_values(args: list, letter: str, valued: str) -> list:
    """The values of the short option `letter` in single-dash clusters before "--": -o dir,
    -odir and -ko dir all give dir. A letter in `valued` takes the rest of its cluster as its
    own value, so a later `letter` in that cluster is not an option."""
    out = []
    for k, a in enumerate(args):
        if a == "--":
            break
        if not a.startswith("-") or a.startswith("--") or a == "-":
            continue
        for p, ch in enumerate(a[1:], 1):
            if ch == letter:
                v = a[p + 1:]
                out.append(v if v else (args[k + 1] if k + 1 < len(args) else ""))
                break
            if ch in valued:
                break
    return out


def _short_flag(args: list, letter: str, valued: str) -> bool:
    """Whether the short option `letter` is given (-f, -qf), read as _short_values reads it."""
    for a in args:
        if a == "--":
            return False
        if not a.startswith("-") or a.startswith("--") or a == "-":
            continue
        for ch in a[1:]:
            if ch == letter:
                return True
            if ch in valued:
                break
    return False


def _long_names(args: list) -> list:
    """The names of the long options before "--", without their "=value"."""
    out = []
    for a in args:
        if a == "--":
            break
        if a.startswith("--") and len(a) > 2:
            out.append(a[2:].split("=", 1)[0])
    return out


def _abbrev(names: list, full: str) -> bool:
    """Whether a long option names `full`, written out or abbreviated: git accepts any prefix
    of a long option that no other option shares (--har is --hard), and refuses the rest, so
    reading every prefix as `full` is never too narrow."""
    return any(n and full.startswith(n) for n in names)


def _long_values(args: list, accepts) -> list:
    """The values of the long options before "--" whose name `accepts`: after "=", or else the
    next word."""
    out = []
    for k, a in enumerate(args):
        if a == "--":
            break
        if a.startswith("--") and len(a) > 2:
            name, eq, value = a[2:].partition("=")
            if accepts(name):
                out.append(value if eq else (args[k + 1] if k + 1 < len(args) else ""))
    return out


def _operands(args: list, short_valued: str = "", long_valued: tuple = ()) -> list:
    """The operands of a git command, without the values of its options. A short option in
    `short_valued` takes the rest of its cluster, or the next word when it ends the cluster; a
    long option that names (or abbreviates) one in `long_valued` takes the next word when it
    has no "=". Every word after "--" is an operand."""
    out, k = [], 0
    while k < len(args):
        a = args[k]
        if a == "--":
            return out + list(args[k + 1:])
        if a.startswith("--"):
            name = a[2:]
            if "=" not in name and any(_abbrev([name], full) for full in long_valued):
                k += 1
        elif a.startswith("-") and a != "-":
            for p, ch in enumerate(a[1:], 1):
                if ch in short_valued:
                    if p == len(a) - 1:
                        k += 1
                    break
        else:
            out.append(a)
        k += 1
    return out


def _git_targets(sub: str, rest: list) -> list:
    """The targets (see Target) of `git <sub> <rest>`, read as item 4 of the docstring says."""
    how = f"git {sub}"
    first = (_operands(rest) or [""])[0]
    longs = _long_names(rest)
    # a file any subcommand writes when --output (or an abbreviation) names it
    out = [(v, False, f"{how} --output")
           for v in _long_values(rest, lambda n: "output".startswith(n) or n.startswith("output"))]
    if not sub:
        return out
    if sub in _GIT_PATHS:
        if sub == "checkout" and (_short_flag(rest, "f", "bB") or _abbrev(longs, "force")):
            return out + [(None, False, "git checkout --force")]
        if _abbrev(longs, "pathspec-from-file"):
            return out + [(None, False, f"{how} --pathspec-from-file")]
        paths = _split_args(rest)[1]
        if sub in ("checkout", "restore") and (_short_flag(rest, "p", "bBs")
                                               or _abbrev(longs, "patch")):
            paths = paths + ["."]   # with or without a path, -p may take every hunk
        return out + [(p, True, how) for p in paths]
    if sub == "switch":
        if (_short_flag(rest, "f", "cC") or _abbrev(longs, "force")
                or _abbrev(longs, "discard-changes") or _abbrev(longs, "orphan")):
            return out + [(None, False, "git switch --discard-changes, --force or --orphan")]
        return out          # a branch switch: not seen (module docstring)
    if sub == "clean":
        if _short_flag(rest, "n", "e") or _abbrev(longs, "dry-run"):
            return out
        paths = _operands(rest, "e", ("exclude",))
        return out + [(p, True, how) for p in (paths or ["."])]
    if sub == "checkout-index":
        prefix = (_long_values(rest, lambda n: bool(n) and "prefix".startswith(n)) or [""])[-1]
        paths = _operands(rest, "", ("prefix", "stage"))
        return out + [(prefix + p, True, how) for p in (paths or ["."])]
    if sub == "reset":
        if any(_abbrev(longs, mode) for mode in ("hard", "merge", "keep")):
            return out + [(None, False, "git reset --hard, --merge or --keep")]
        return out          # the index only
    if sub in ("apply", "am"):
        # a report only, unless --apply asks for the patch to be applied as well
        if (not any(_abbrev(longs, o) for o in ("check", "stat", "numstat", "summary"))
                or _abbrev(longs, "apply")):
            out.append((None, False, how))
        return out
    if sub in _GIT_REFUSED:
        return out + [(None, False, how)]
    if sub in _GIT_READ_FORMS:
        if first not in _GIT_READ_FORMS[sub]:
            out.append((None, False, f"{how} {first}".rstrip()))
        return out
    if sub == "format-patch":
        dirs = (_short_values(rest, "o", _FORMAT_PATCH_VALUED)
                + _long_values(rest, lambda n: n.startswith("output-d")))
        if not dirs and not _abbrev(longs, "stdout"):
            dirs = ["."]    # the patches land in the current directory
        return out + [(d, False, how) for d in dirs]
    if sub == "archive":
        return out + [(v, False, how) for v in _short_values(rest, "o", "")]
    if sub == "bundle":
        if first == "create":
            ops = _operands(rest)
            out += [(ops[1], False, "git bundle create")] if len(ops) > 1 else []
        return out
    if sub == "config":
        files = (_short_values(rest, "f", "")
                 + _long_values(rest, lambda n: bool(n) and "file".startswith(n)))
        return out + [(f, False, "git config --file") for f in files]
    if sub == "init":
        ops = _operands(rest, "b", ("template", "separate-git-dir", "object-format",
                                    "ref-format", "initial-branch")) or ["."]
        out += [(p, False, how) for p in ops]
        return out + [(v, False, how)
                      for v in _long_values(rest, lambda n: n.startswith("separate-git"))]
    if sub == "worktree":
        ops = _operands(rest, "bB", ("reason",))
        action, ops = (ops[0], ops[1:]) if ops else ("", [])
        if action == "add":
            return out + [(p, False, "git worktree add") for p in ops]
        if action in ("remove", "move"):
            out += [(p, True, f"git worktree {action}") for p in ops[:1]]
            return out + [(p, False, "git worktree move") for p in ops[1:2]]
        if action not in ("", "list", "prune", "lock", "unlock", "repair"):
            out.append((None, False, f"git worktree {action}"))
        return out
    if sub in _GIT_READS:
        return out
    return out + [(None, False, f"git {sub}, a subcommand this hook does not read "
                                f"(an alias, say)")]


def _command_name(word: str) -> str:
    """The command a word names: its basename, read without the g of a GNU tool installed
    under a g prefix (_GNU_PREFIXED: grm is rm, gtimeout is timeout; git stays git)."""
    name = os.path.basename(word)
    return name[1:] if name[:1] == "g" and name[1:] in _GNU_PREFIXED else name


def _add_bases(bases: list, dest: str) -> None:
    """Add the directory `dest`, read against every base so far, to `bases` (cd, pushd, git
    -C, env -C, sudo -D). Each such directory can double the bases, so it is paid for."""
    _spend(len(bases))
    dest = os.path.expanduser(os.path.expandvars(dest))
    known = set(bases)
    for b in list(bases):
        nb = os.path.normpath(os.path.join(b, dest))
        if nb not in known:
            known.add(nb)
            bases.append(nb)


def _prefix_starts(name: str, ws: list, j: int, bases: list, out: list, marker) -> tuple:
    """Where the command that the wrapper `name` runs may start, reading from ws[j]: (the
    positions in ws, the word lists env -S makes, whether the words ran out while a value or
    the command was still to come).

    A word may be read two ways: as the value of the option before it, and as a word in its
    own right. An option in _PREFIX_OPTIONS settles which (in sudo -u me, me is a value and
    nothing else); an option missing from the table settles nothing, so the next word is
    read both ways. A word in its own right is an option, "--", an assignment, a number or a
    lone "-" (the last three passed over), or else the command, which ends that reading.
    Every position some reading takes for the command is returned and the caller keeps the
    targets of each, so a wrong guess about an unknown option can only make a harmless
    command look like a write (and be refused), never hide one.

    A long option is matched as getopt_long matches it: a name written out in full is that
    option, even when it is also the start of a longer one (sudo --login is a flag, though
    --login-class takes a value); only a name that is not written out in full is read as a
    prefix, and a prefix that a flag and a valued option share reads the next word both ways.
    "--" switches option parsing off, and does not name the command by itself: the words
    after it are still read in their own right, so assignments, numbers and a lone "-" are
    passed over there too, and a word that starts with "-" is the command. The words after
    "--" are read with options on as well, as if it were not there, so a wrapper that does
    not honour "--" (or that this table reads wrongly) cannot hide its command behind one;
    the price is only that a command no wrapper would run (env -- -i rm) looks like a write.
    timeout's first operand is its DURATION, which GNU timeout reads with strtod, so any
    spelling may be one (10, 10s, 1e3, inf, 0x10, +5), before "--" or after it: it is passed
    over, and read as the command as well, in case it is not the duration.

    The values in _PREFIX_EFFECTS act as they are read: env -C and sudo -D add a base, as cd
    does; time -o adds the file it writes to `out`; env -S gives a new word list, env, then
    the words of the split string, then the words after it, which the caller reads as
    well. sudo -e (--edit) runs no command: the words it would take for one are the files it
    opens in an editor, and they go to `out` as written. A value or a file that holds the
    xargs `marker` comes from xargs's input and is refused, as _command_targets says."""
    short_flags, short_valued, long_flags, long_valued = _PREFIX_OPTIONS.get(
        name, ("", "", (), ()))
    effects = _PREFIX_EFFECTS.get(name, {})
    starts, splits = [], []
    edits = False

    def act(kinds: list, value: str, at: int) -> None:
        for kind in kinds:
            if marker is not None and marker in value and kind != "split":
                # the split words carry the marker on, and their reading judges it
                out.append((None, False, f"xargs {name}, with an option value from its input"))
            elif kind == "chdir":
                _add_bases(bases, value)
            elif kind == "write":
                out.append((value, False, f"{name} -o"))
            elif kind == "split":
                splits.append(["env"] + [t for t, _ in _lex(value)] + list(ws[at + 1:]))
                _spend(len(splits[-1]))

    # Every live reading of ws[j]: (whether it is read in its own right rather than as a
    # value, the effects of the option it is the value of, whether "--" has switched option
    # parsing off, whether timeout's duration is still to come). A set, so readings that
    # meet again are read once.
    readings = {(True, (), False, name == "timeout")}
    while j < len(ws) and readings:
        _spend(len(readings))
        a = ws[j]
        after = set()
        for own, pending, ended, duration in readings:
            if not own:
                act(list(pending), a, j)
                after.add((True, (), ended, duration))
            elif not ended and a == "--":
                after.add((True, (), True, duration))
                after.add((True, (), False, duration))  # a wrapper that does not honour it
            elif not ended and a.startswith("--"):
                opt, eq, value = a[2:].partition("=")
                flag, valued = opt in long_flags, opt in long_valued
                if flag or valued:
                    # written out in full: that option, whatever longer one it starts
                    kinds = (effects[opt],) if valued and len(opt) > 1 and opt in effects else ()
                else:
                    # getopt_long takes any unshared prefix of a long option, as git does
                    flag = any(f.startswith(opt) for f in long_flags)
                    valued = any(f.startswith(opt) for f in long_valued)
                    kinds = tuple(kind for f, kind in effects.items()
                                  if len(f) > 1 and f.startswith(opt))
                edits = edits or (name == "sudo" and not eq and "edit".startswith(opt))
                if eq:
                    act(list(kinds), value, j)
                    after.add((True, (), False, duration))
                    continue
                if valued or not flag:      # a valued option, a shared prefix or an unknown
                    after.add((False, kinds, False, duration))
                if flag or not valued:      # a flag, a shared prefix or an unknown
                    after.add((True, (), False, duration))
            elif not ended and a.startswith("-") and a != "-":
                for p, ch in enumerate(a[1:], 1):
                    edits = edits or (name == "sudo" and ch == "e")
                    if ch in short_valued:
                        kinds = (effects[ch],) if ch in effects else ()
                        if a[p + 1:]:                  # -uroot, -oL: the value is glued
                            act(list(kinds), a[p + 1:], j)
                            after.add((True, (), False, duration))
                        else:
                            after.add((False, kinds, False, duration))
                        break
                    if ch not in short_flags:
                        after.add((False, (), False, duration))
                        after.add((True, (), False, duration))
                        break
                else:
                    after.add((True, (), False, duration))
            elif duration:
                # timeout's DURATION, in any spelling strtod reads; the command, if it is not
                starts.append(j)
                after.add((True, (), ended, False))
            elif a == "-" or _ASSIGNMENT_RE.match(a) or _NUMBER_RE.match(a):
                after.add((True, (), ended, False))    # a lone "-" is env's -i
            else:
                starts.append(j)
        readings = after
        j += 1
    if edits and starts:
        out += [(None, False, "xargs sudo -e, with files from its input")
                if marker is not None and marker in f else (f, False, "sudo -e")
                for f in ws[min(starts):] if not f.startswith("-")]
    return sorted(set(starts)), splits, bool(readings)


def _command_targets(words: list, bases: list, depth: int) -> list:
    """The targets of one simple command (see Target); `bases` gains a directory named by cd,
    pushd, git -C, env -C or sudo -D.

    Assignments before the command are passed over. A wrapper (_PREFIXES) is read by
    _prefix_starts, and the command it runs is read at every position that may start it;
    the targets of every reading count.

    A command run by xargs gets the words xargs reads from its input: appended (stood for by
    _APPENDED), or put where its replace string (-I, -J, -i, --replace) stands. A target that
    holds one of them is a path this hook cannot see, and the command is refused, except
    where cp, ln and the like copy such a word into a named directory: then that directory
    is judged as one that may come to hold any name. A command whose name holds one of them
    is refused too (xargs env, xargs -I{} {}), and so is a wrapper whose words run out before
    its command does (xargs sudo -u): its input names the command. xargs given no command
    runs echo, and changes nothing.

    Past _MAX_DEPTH (find -exec inside find -exec) the command is refused, not let through.

    A reading is (which word list, the position the command may start at, the xargs marker).
    The word lists are this command's words, a list with _APPENDED added for each xargs that
    appends (made once per list), and each distinct list env -S makes. A reading is queued
    once, however many readings reach it, so a run of wrappers is read in time linear in the
    readings; _spend refuses a command whose readings run past _MAX_WORK."""
    if depth > _MAX_DEPTH:
        return [_TOO_DEEP]
    out = []
    lists = [list(words)]
    appended = {}           # a list's index -> the index of that list with _APPENDED added
    split_at = {}           # the words of a list env -S made -> its index
    todo = collections.deque([(0, 0, None)])
    queued = {(0, 0, None)}

    def push(at: int, k: int, marker) -> None:
        if (at, k, marker) not in queued:
            queued.add((at, k, marker))
            todo.append((at, k, marker))

    while todo:
        at, k, marker = todo.popleft()
        _spend(1)
        ws = lists[at]
        while k < len(ws):
            w = ws[k]
            if _ASSIGNMENT_RE.match(w):
                k += 1
            elif _command_name(w) == "xargs":
                replace = None
                k += 1
                while k < len(ws) and ws[k].startswith("-") and ws[k] != "-":
                    a = ws[k]
                    k += 1
                    if a == "--":
                        break
                    if a.startswith("--"):
                        # getopt_long, like git, takes any unshared prefix of a long option
                        opt, eq, value = a[2:].partition("=")
                        if _abbrev([opt], "replace"):
                            replace = value if eq else "{}"
                        elif not eq and any(_abbrev([opt], v[2:]) for v in _XARGS_VALUED
                                            if v.startswith("--")):
                            k += 1
                        continue
                    for p, ch in enumerate(a[1:], 1):
                        if "-" + ch in _XARGS_VALUED:      # -I {}, -I{}, -0I {}
                            value = a[p + 1:]
                            if not value:
                                value = ws[k] if k < len(ws) else ""
                                k += 1
                            if ch in "IJ":
                                replace = value
                            break
                        if ch in "iel":                    # GNU: an optional value, glued
                            if ch == "i":
                                replace = a[p + 1:] or "{}"
                            break
                if k >= len(ws):
                    break                                  # no command: xargs runs echo
                if replace is None:
                    if at not in appended:
                        lists.append(ws + [_APPENDED])
                        appended[at] = len(lists) - 1
                        _spend(len(ws))
                    at = appended[at]
                    ws = lists[at]
                    marker = _APPENDED
                else:
                    marker = replace
            elif _command_name(w) in _PREFIXES:
                starts, splits, open_end = _prefix_starts(_command_name(w), ws, k + 1,
                                                          bases, out, marker)
                for s in starts:
                    push(at, s, marker)
                for split in splits:
                    key = tuple(split)
                    if key not in split_at:
                        lists.append(split)
                        split_at[key] = len(lists) - 1
                    push(split_at[key], 0, marker)
                if open_end and marker == _APPENDED:
                    # xargs sudo -u: its input fills the value, then names the command
                    out.append((None, False, "xargs, with a command its input names"))
                k = len(ws)
            else:
                break
        if k >= len(ws):
            continue
        name = _command_name(ws[k])
        if marker is not None and marker in ws[k]:
            out.append((None, False, "xargs, with a command its input names"))
            continue
        found = _named_targets(name, list(ws[k + 1:]), bases, depth, marker)
        if marker is not None:
            found = [(None, False, f"xargs {name}, whose paths come from its input")
                     if p is not None and marker in p else (p, holds, how)
                     for p, holds, how in found]
        out += found
    return out


def _named_targets(name: str, args: list, bases: list, depth: int, marker) -> list:
    """The targets of the command `name` with its arguments (see _command_targets)."""
    opts, plain = _split_args(args)
    out = []

    if name in ("cd", "pushd"):
        dest = plain[0] if plain else "~"
        if dest != "-":
            _add_bases(bases, dest)
    elif name in _SHELLS:
        for j, a in enumerate(args):
            if a.startswith("-") and not a.startswith("--") and "c" in a[1:]:
                if j + 1 < len(args):
                    out += _shell_targets(args[j + 1], bases, depth + 1)
                break
    elif name == "eval":
        out += _shell_targets(" ".join(args), bases, depth + 1)
    elif name in _REMOVES:
        out += [(p, True, name) for p in plain]
    elif name in _WRITES or name == "sudoedit":
        out += [(p, False, name) for p in plain]
    elif name == "dd":
        out += [(a[3:], False, "dd of=") for a in args if a.startswith("of=")]
    elif name in _IN_PLACE:
        if any(_IN_PLACE[name].match(o) for o in opts):
            out += [(p, False, f"{name} in place") for p in plain]
    elif name in _COPIES:
        tdir = next((a.split("=", 1)[1] for a in opts if a.startswith("--target-directory=")),
                    None)
        for j, a in enumerate(args):
            if a == "-t" and j + 1 < len(args):
                tdir = args[j + 1]
                plain = [p for p in plain if p != tdir]
        if tdir is not None:
            dest, sources = tdir, plain
        elif len(plain) >= 2:
            dest, sources = plain[-1], plain[:-1]
        elif name == "ln" and plain:
            dest, sources = ".", plain
        else:
            dest, sources = None, []
        if dest is not None:
            out.append((dest, False, name))
            for s in sources:
                if marker is not None and marker in s:
                    # a name xargs supplies lands in dest: dest may come to hold any name
                    out.append((dest, True, name))
                else:
                    out.append((os.path.join(dest, os.path.basename(s.rstrip("/"))), False,
                                name))
        if name == "mv":
            out += [(s, True, "mv (its source)") for s in sources]
    elif name == "git":
        j = 0
        while j < len(args) and args[j].startswith("-"):
            if args[j] == "-C" and j + 1 < len(args):
                _add_bases(bases, args[j + 1])
                j += 2
            elif args[j] in ("-c", "--git-dir", "--work-tree", "--namespace") and j + 1 < len(args):
                j += 2
            else:
                j += 1
        sub, rest = (args[j], args[j + 1:]) if j < len(args) else ("", [])
        out += _git_targets(sub, rest)
    elif name == "patch":
        if "--dry-run" not in args:
            out.append((None, False, "patch"))
    elif name == "find":
        starts = []
        for a in args:
            if a.startswith("-") or a in ("(", "!", ")"):
                break
            starts.append(a)
        if any(a in _FIND_ACTIONS for a in args):
            out += [(p, True, "find") for p in (starts or ["."])]
        for j, a in enumerate(args):
            if a in ("-exec", "-execdir", "-ok", "-okdir"):
                sub_words = []
                for b in args[j + 1:]:
                    if b in (";", "+"):
                        break
                    sub_words.append(b)
                _spend(len(sub_words))
                out += _command_targets(sub_words, bases, depth + 1)
    return out


def _shell_targets(command: str, bases: list, depth: int = 0) -> list:
    """Every target (see Target) of a shell command, read as item 4 of the docstring says.

    A command that holds an escaped backtick outside single quotes is refused whole: in a
    backtick substitution that is how another one is nested, and _lex reads it as text."""
    if depth > _MAX_DEPTH:
        return [_TOO_DEEP]
    nested = []
    lexed = _lex(command, nested)
    _spend(len(lexed))
    if nested:
        return [(None, False, _NESTED_BACKTICK)]
    out = []
    for text, is_op in lexed:
        if not is_op and ("$(" in text or "`" in text):
            for inner in _substituted(text):
                out += _shell_targets(inner, bases, depth + 1)
    for words, writes in _simple_commands(lexed):
        out += [(w, False, "a redirection") for w in writes]
        out += _command_targets(words, bases, depth)
    return out


def _touches(rel: str, holds: bool) -> bool:
    """Whether a path relative to the repository is forbidden, is a forbidden directory itself
    (tools/hooks), or, when `holds`, is a directory that holds a forbidden path."""
    key = rel.rstrip("/")
    if forbidden(key) or forbidden(key + "/"):
        return True
    if holds:
        k = key.casefold() + "/"
        return any(p.casefold().startswith(k) for p in FORBIDDEN_PREFIXES + FORBIDDEN_EXACT)
    return False


def _holds_repository(path: str, cwd: str) -> bool:
    """Whether `path` is the repository root or a directory above it. The roots are the
    marked ancestors of the cwd and of CLAUDE_PROJECT_DIR; only when there is none are the two
    themselves the roots, as in repo_relatives."""
    t = _nfc(os.path.realpath(os.path.normpath(path))).rstrip("/")
    project = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    starts = [s for s in (cwd, project) if s]
    roots = set()
    for start in starts:
        d = start
        while True:
            if _marked(d):
                roots.add(_nfc(os.path.realpath(d)))
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    if not roots:
        roots = {_nfc(os.path.realpath(s)) for s in starts}
    return any(r == t or r.startswith(t + "/") for r in roots)


def _glob_names(d: str, pattern: str, dironly: bool) -> list:
    """glob._glob1: the names in directory `d` that `pattern` matches, a hidden name only
    when the pattern starts with a dot, and only directories when `dironly`. Each entry read
    is a step, matched or not."""
    names = []
    try:
        with os.scandir(d or os.curdir) as entries:
            for entry in entries:
                _spend(1)
                try:
                    if not dironly or entry.is_dir():
                        names.append(entry.name)
                except OSError:
                    pass
    except (OSError, ValueError):
        pass        # as glob does: what was read before the error is kept
    if pattern[:1] != ".":
        names = [n for n in names if n[:1] != "."]
    return fnmatch.filter(names, pattern)


def _glob_exists(d: str, name: str) -> bool:
    """glob._glob0, for a name without wildcards: one lookup, one step. An empty name (the
    pattern ended with a slash) asks for a directory."""
    _spend(1)
    return os.path.lexists(os.path.join(d, name)) if name else os.path.isdir(d)


def _glob(pattern: str) -> list:
    """The first _MAX_GLOB paths glob.glob(pattern) gives, in its order, read with every
    directory entry and every lookup spent as a step (_spend), so the work budget bounds a
    glob that matches nothing as it bounds one that matches much. The directories are
    walked from an explicit stack, not by recursion, so a deep pattern cannot overflow."""
    head, tails = pattern, []
    while _GLOB_MAGIC.search(head):
        head, tail = os.path.split(head)
        tails.append(tail)
        if not head:
            break
    if not tails:
        return [pattern] if _glob_exists(*os.path.split(pattern)) else []
    parts = tails[::-1]
    out = []
    stack = [(head, 0)]         # a path matched through parts[:i], and i
    while stack:
        path, i = stack.pop()
        if i == len(parts):
            out.append(path)
            if len(out) >= _MAX_GLOB:
                break
            continue
        part = parts[i]
        if _GLOB_MAGIC.search(part):
            names = _glob_names(path, part, i < len(parts) - 1)
        else:
            names = [part] if _glob_exists(path, part) else []
        stack += [(os.path.join(path, n), i + 1) for n in reversed(names)]
    return out


_NO_TIMER = object()


def _start_timer():
    """Start the _MAX_SECONDS timer, and return the SIGALRM handler to put back. Where there
    is no timer to use (no SIGALRM, as on Windows; a caller off the main thread; a caller's
    own timer already running, which is left alone) return _NO_TIMER: the steps alone then
    bound the reading."""
    try:
        if signal.getitimer(signal.ITIMER_REAL)[0] > 0:
            return _NO_TIMER
        previous = signal.signal(signal.SIGALRM, _out_of_time)
    except (AttributeError, ValueError, OSError):
        return _NO_TIMER
    signal.setitimer(signal.ITIMER_REAL, _MAX_SECONDS)
    return previous


def _stop_timer(previous) -> None:
    if previous is not _NO_TIMER:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, signal.SIG_DFL if previous is None else previous)


def shell_hit(command: str, cwd: str) -> "tuple | None":
    """(what, how) for the first forbidden change a shell command makes, or None. A command
    longer than _MAX_COMMAND characters, or one that takes more than _MAX_WORK steps (_spend)
    or _MAX_SECONDS to read, gives (None, _TOO_LONG and the limit): it is refused, not read
    until the hook times out. The seconds are a backstop for work no step counts (a system
    call that is slow on some filesystem, say), kept by a SIGALRM timer where there is one
    (_start_timer); the timer is stopped, and the caller's handler put back, before this
    returns."""
    global _work_done
    if len(command) > _MAX_COMMAND:
        return None, f"{_TOO_LONG} (over {_MAX_COMMAND} characters)"
    _work_done = 0
    try:
        previous = _start_timer()
        try:
            hit = _first_hit(command, cwd)
        finally:
            _stop_timer(previous)
    except _TooLong as limit:
        # outside the finally, so a timer that fires while it is being stopped still refuses
        return None, f"{_TOO_LONG} ({limit})"
    return hit


def _first_hit(command: str, cwd: str) -> "tuple | None":
    """shell_hit, within the work budget (_spend). A path is judged once, however many
    targets name it."""
    project = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    bases = [cwd or project or os.getcwd()]
    judged = set()
    for path, holds, how in _shell_targets(command, bases):
        if path is None:
            return None, how
        p = os.path.expanduser(os.path.expandvars(path))
        if (p, holds) in judged:
            continue
        judged.add((p, holds))
        cands = []
        for b in bases:
            full = p if os.path.isabs(p) else os.path.join(b, p)
            cands.append(full)
            if _GLOB_MAGIC.search(p):
                cands += _glob(full)
        for c in cands:
            _spend(_JUDGE_STEPS)
            for rel in repo_relatives(c, cwd):
                if _touches(rel, holds):
                    return rel, how
            if holds and _holds_repository(c, cwd):
                return path, how
    return None


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    cwd = payload.get("cwd") or ""
    cwd = cwd if isinstance(cwd, str) else ""

    # ── claim-bearing tools, invoked through the shell ───────────────────────
    command = tool_input.get("command") or ""
    if command:
        if not isinstance(command, str):
            return 0
        for tool in FORBIDDEN_TOOLS:
            if re.search(rf"\b{re.escape(tool)}\b", command):
                return block(
                    f"You may not run {tool}. It moves the canonical assertion count, which is\n"
                    f"a claim, and claims are not the tester's to move — the same reason\n"
                    f"run_tests.py is off-limits to you.\n\n"
                    f"Finish your verdict and hand off. architect-pm runs capture and sync as\n"
                    f"its own step, after your suite is registered. See DECISIONS D-016.\n")
        # ── files changed through the shell (item 4) ────────────────────────
        try:
            hit = shell_hit(command, cwd)
        except Exception:
            return 0
        if hit is None:
            return 0
        what, how = hit
        if what is None:
            advice = next((a for reason, a in _ADVICE.items() if how.startswith(reason)), "")
            return block(
                f"You may not run {how}: it can change any path, src/ and this lane's own\n"
                f"guard included, and this hook cannot see which.\n\n{advice}{HANDBACK}")
        return block(
            f"You may create and edit test files and harnesses only\n"
            f"(tests/test_tester_*.py). This command changes {what} through the shell\n"
            f"({how}), which you may not modify.\n\n{HANDBACK}")

    # ── files ────────────────────────────────────────────────────────────────
    target = (tool_input.get("file_path") or tool_input.get("notebook_path")
              or tool_input.get("path") or "")
    if not target or not isinstance(target, str):
        return 0
    try:
        rels = repo_relatives(target, cwd)
    except Exception:
        return 0

    hit = next((r for r in rels if forbidden(r)), None)
    if hit is not None:
        return block(
            f"You may create and edit test files and harnesses only\n"
            f"(tests/test_tester_*.py). You may not modify {hit}.\n\n{HANDBACK}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
