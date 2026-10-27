#!/usr/bin/env python3
"""og.py — the social image names the active stage; this keeps the name true (D-031).

The card that every page's link preview shows (website/public/og.png, a byte copy of
brand/psyche-social.png) has the active stage written into its pixels, as "STAGE 2 · SPIKING
COGNITIVE MAPS". Nothing in a build can read pixels, so the card is never edited by hand: it is
drawn by website/scripts/make-og.mjs (`npm run og` in website/), which renders an HTML template
with headless Chrome using the card text this module derives from the ledger's program state
(`--card`). The generator records the stage line it drew in two places: in the PNG itself, as a
tEXt chunk named "psyche-stage" written at the moment it rendered that text, and in
brand/psyche-social.json beside the image, together with the sha256 of the PNG.

    python3 tools/publish/og.py --check    fail unless the stage line the PNG carries and the one the
                                           sidecar records are the one the ledger's program state gives
                                           now, the sidecar describes brand/psyche-social.png byte for
                                           byte, and website/public/og.png is a byte copy of it
    python3 tools/publish/og.py --card     print the card text as JSON (what the generator draws)

So when the project lead changes `program` in tools/ledger.json (a stage resumes, pauses or
closes) the build fails until the card is drawn again. An image replaced by hand fails (the hash no
longer matches the sidecar), and so does a sidecar edited to match the ledger without a new image
(the image still carries the old stage line). What this cannot know is whether the pixels say what
the PNG's own text chunk says: only the generator writes both, and a hand that rewrites the chunk
and the sidecar and the hash together is forging, which no check can stop. That is the contract.

The stage numbers are fixed here, not read from the ledger: stage 1 is the substrate and stage 2
the cognitive-map line (CONTRIBUTING.md). A line of the program block with no entry in STAGES is
refused, so a stage 3 cannot be added to the ledger and slip past the card.

Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402

CARD_REL = "brand/psyche-social.png"
SIDECAR_REL = "brand/psyche-social.json"
PUBLIC_REL = "website/public/og.png"
GENERATOR_REL = "website/scripts/make-og.mjs"
CARD_SIZE = (1200, 630)

DOT = "·"
URL_TEXT = "cagancaliskan.github.io/psyche"
# The line under the wordmark: the project, in the words CONTRIBUTING.md gives, with its aim named
# as an aim.
TAGLINE = ("An open research project that builds brain-inspired components in stages, with "
           "artificial general intelligence as its long-term aim.")

# program line -> (stage number, the stage's name as the card shows it)
STAGES: Dict[str, Tuple[int, str]] = {
    "substrate": (1, "The substrate"),
    "cognitive_map": (2, "Spiking cognitive maps"),
}
SIDECAR_KEYS = ("stage", "tagline", "alt", "sha256", "width", "height", "generator")

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
TEXT_KEYWORD = "psyche-stage"


def stage_label(states: Dict[str, str]) -> str:
    """The stage line of the card for the given program states ({line: state}). A stage is named
    when its line is active; with none active the card says so rather than keep a stage's name."""
    active = sorted((STAGES[line][0], STAGES[line][1]) for line, st in states.items() if st == "active")
    if not active:
        return "No stage active"
    numbers = [str(n) for n, _ in active]
    names = [name if i == 0 else name[0].lower() + name[1:] for i, (_, name) in enumerate(active)]
    head = f"Stage {numbers[0]}" if len(active) == 1 else "Stages " + " and ".join(numbers)
    return f"{head} {DOT} {' and '.join(names)}"


def program_states(root: Path) -> Dict[str, str]:
    """{line: state} for every line of the ledger's program block, refusing a line the card has
    no stage number for."""
    led = core.load_ledger(root)
    program = led.get("program")
    if not isinstance(program, dict):
        raise core.PublishError(f"{core.LEDGER_REL.as_posix()}: program is not an object")
    states: Dict[str, str] = {}
    for key, value in program.items():
        if not (isinstance(value, dict) and "state" in value):
            continue                      # _README, aim, aim_rule
        if key not in STAGES:
            raise core.PublishError(
                f"{core.LEDGER_REL.as_posix()}: program.{key} has no stage number in "
                f"tools/publish/og.py (STAGES); add it there and draw the card again")
        if not isinstance(value["state"], str):
            raise core.PublishError(f"{core.LEDGER_REL.as_posix()}: program.{key}.state is not a string")
        states[key] = value["state"]
    missing = [k for k in STAGES if k not in states]
    if missing:
        raise core.PublishError(f"{core.LEDGER_REL.as_posix()}: program lacks {', '.join(missing)}")
    return states


def card(root: Path) -> Dict[str, object]:
    """What the generator draws, and what the sidecar records, for the ledger as it stands."""
    label = stage_label(program_states(root))
    return {
        "stage": label,
        "tagline": TAGLINE,
        "url": URL_TEXT,
        "alt": f"Psyche. {label}. {TAGLINE}",
    }


def png_size(data: bytes) -> Optional[Tuple[int, int]]:
    """(width, height) of a PNG from its header, or None when `data` is not one."""
    if len(data) < 24 or data[:8] != _PNG_MAGIC or data[12:16] != b"IHDR":
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def png_text(data: bytes) -> Dict[str, str]:
    """The tEXt chunks of a PNG ({keyword: text}, Latin-1 as the format says), read to the end of
    the chunk list. Stops at the first chunk that does not fit the bytes; never raises."""
    out: Dict[str, str] = {}
    if data[:8] != _PNG_MAGIC:
        return out
    pos = 8
    while pos + 8 <= len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if len(body) != length:
            break
        if kind == b"tEXt" and b"\x00" in body:
            keyword, _, text = body.partition(b"\x00")
            out.setdefault(keyword.decode("latin-1"), text.decode("latin-1"))
        if kind == b"IEND":
            break
        pos += 12 + length
    return out


def check(root: Path) -> List[str]:
    """Every problem, or []."""
    root = Path(root).resolve()
    try:
        want = card(root)
    except core.PublishError as e:
        return [str(e)]
    redo = f"run `npm run og` in website/ and commit {CARD_REL}, {PUBLIC_REL} and {SIDECAR_REL}"
    problems: List[str] = []

    side_path = root / SIDECAR_REL
    if not side_path.is_file():
        return [f"{SIDECAR_REL}: missing; {redo}"]
    try:
        side = core.parse_json(side_path.read_text(encoding="utf-8"), SIDECAR_REL)
    except (core.PublishError, OSError, ValueError) as e:
        return [f"{SIDECAR_REL}: not readable JSON ({e}); {redo}"]
    if not isinstance(side, dict):
        return [f"{SIDECAR_REL}: not a JSON object; {redo}"]
    odd = sorted(set(side) ^ set(SIDECAR_KEYS))
    if odd:
        problems.append(f"{SIDECAR_REL}: keys {odd} are missing or unknown (expected {list(SIDECAR_KEYS)}); {redo}")

    if side.get("stage") != want["stage"]:
        problems.append(
            f"{CARD_REL} was drawn for the stage line {side.get('stage')!r}, and the ledger's program "
            f"state now gives {want['stage']!r}; {redo}")
    if side.get("tagline") != want["tagline"]:
        problems.append(f"{SIDECAR_REL}: the tagline drawn is not the one tools/publish/og.py gives; {redo}")
    if side.get("alt") != want["alt"]:
        problems.append(f"{SIDECAR_REL}: the alt text is not the one tools/publish/og.py gives; {redo}")

    digest = side.get("sha256")
    for rel in (CARD_REL, PUBLIC_REL):
        path = root / rel
        if not path.is_file():
            problems.append(f"{rel}: missing; {redo}")
            continue
        data = path.read_bytes()
        if (side.get("width"), side.get("height")) != CARD_SIZE or png_size(data) != CARD_SIZE:
            problems.append(f"{rel}: must be a PNG of {CARD_SIZE[0]} x {CARD_SIZE[1]} and say so in "
                            f"{SIDECAR_REL}")
        carried = png_text(data).get(TEXT_KEYWORD)
        if carried != want["stage"]:
            problems.append(
                f"{rel} carries the stage line {carried!r} and the ledger's program state now gives "
                f"{want['stage']!r}; the image was drawn for another state or not by {GENERATOR_REL}; {redo}")
        if hashlib.sha256(data).hexdigest() != digest:
            problems.append(f"{rel}: is not the image {SIDECAR_REL} describes (sha256 differs); the card "
                            f"is drawn by {GENERATOR_REL}, never edited or replaced by hand; {redo}")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true",
                      help="fail unless the social image was drawn for the ledger's program state")
    mode.add_argument("--card", action="store_true", help="print the card text as JSON")
    ap.add_argument("--root", default=str(core.REPO), help="repository root")
    args = ap.parse_args(argv)
    root = Path(args.root)
    try:
        if args.card:
            print(json.dumps(card(root), ensure_ascii=False, indent=1))
            return 0
        problems = check(root)
    except core.PublishError as e:
        print(f"og: {e}", file=sys.stderr)
        return 2
    for p in problems:
        print(f"og: {p}", file=sys.stderr)
    if problems:
        print(f"og: {len(problems)} problem(s)", file=sys.stderr)
        return 1
    print(f"og: {CARD_REL} and {PUBLIC_REL} were drawn for {card(root)['stage']!r}, "
          f"the ledger's active stage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
