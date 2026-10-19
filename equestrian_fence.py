#!/usr/bin/env python3
"""EquestrianFence - lay out a rectangular horse-pasture fence from the terminal.

Three subcommands, standard library only, no files written and no network used:

    layout     four compass-named runs, perimeter and a corner-deduplicated post count
    spacing    fit a whole number of equal post segments to a single run
    checklist  numbered gate openings plus the three named placement checks

Design source of truth is THEME below: calm-precise, terminal dark, system
monospace, aligned columns, one accent (oklch(0.58 0.12 204) / #008e9b) used for
primary status only, never as the sole signal (every coloured value also carries
a word or a symbol). Colour is emitted only on a TTY and never when NO_COLOR is
set, so piped output stays deterministic plain ASCII.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from typing import Any, Sequence

__version__ = "1.0.0"

PROG = "equestrianfence"

# --------------------------------------------------------------------------
# Design tokens (committed design direction - every rendered line consumes these)
# --------------------------------------------------------------------------

THEME: dict[str, Any] = {
    "accent_oklch": "oklch(0.58 0.12 204)",
    "accent_hex": "#008e9b",
    "accent_rgb": (0, 142, 155),      # the same accent, for 24-bit terminal colour
    "muted_rgb": (132, 145, 150),     # neutral ramp step for secondary text
    "rule_rgb": (86, 98, 104),        # neutral ramp step for separators
    "surface": "terminal dark",
    "type": "system monospace",
    "density": "compact",
}

# A subcommand never prints more than this many lines; gate lists are capped
# (with an explicit "n more" line) so a huge --gates value cannot flood a terminal.
MAX_LINES = 40
MAX_LISTED_GATES = 16

# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class ValidationError(Exception):
    """A user input problem: carries the field, the message and exit code 2."""

    def __init__(self, field: str, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.field = field
        self.message = message
        self.exit_code = exit_code


class UsageError(Exception):
    """An argparse usage problem (missing argument, unknown subcommand)."""

    def __init__(self, message: str, example: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.example = example


# --------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Style:
    """Paints text with the committed accent/neutral tokens, or does nothing."""

    enabled: bool = False

    def _paint(self, text: str, rgb: tuple[int, int, int]) -> str:
        if not self.enabled or not text:
            return text
        red, green, blue = rgb
        return f"\x1b[38;2;{red};{green};{blue}m{text}\x1b[0m"

    def accent(self, text: str) -> str:
        return self._paint(text, THEME["accent_rgb"])

    def muted(self, text: str) -> str:
        return self._paint(text, THEME["muted_rgb"])

    def rule(self, text: str) -> str:
        return self._paint(text, THEME["rule_rgb"])


PLAIN = Style(enabled=False)


def colour_enabled(stream: Any) -> bool:
    """Colour only for a real terminal, and never when NO_COLOR is set."""
    if os.environ.get("NO_COLOR") is not None:
        return False
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


# --------------------------------------------------------------------------
# Number formatting (at most two decimals, never scientific notation)
# --------------------------------------------------------------------------


def feet(value: float) -> str:
    """`100`, `12.5`, `12.55` - trimmed, at most two decimals."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text if text else "0"


def feet_precise(value: float) -> str:
    """`12.50`, `10.00`, `0.00` - always two decimals."""
    text = f"{value:.2f}"
    return "0.00" if text == "-0.00" else text


def feet_signed(value: float) -> str:
    """`+0.50`, `-0.12`, `0.00`."""
    if round(value, 2) == 0:
        return "0.00"
    return f"{value:+.2f}"


def count(value: int) -> str:
    return f"{value:,}"


# --------------------------------------------------------------------------
# Validation (one shared code path for all three subcommands)
# --------------------------------------------------------------------------


def positive_float(field: str, raw: str | None, flag: str = "") -> float:
    """Parse a required positive number or raise ValidationError with exit code 2."""
    text = (raw or "").strip()
    if not text:
        missing = f"missing {flag}" if flag else "no value given"
        raise ValidationError(field, f"{field} must be a number: {missing}")
    try:
        value = float(text)
    except ValueError:
        raise ValidationError(
            field, f"{field} must be a number, got '{text}'"
        ) from None
    if not math.isfinite(value):
        raise ValidationError(field, f"{field} must be a number, got '{text}'")
    if value <= 0:
        raise ValidationError(
            field, f"{field} must be a positive number, got {text}"
        )
    return value


def positive_count(field: str, raw: str | None, flag: str = "") -> int:
    """A positive whole number (gates are counted, not measured)."""
    value = positive_float(field, raw, flag)
    nearest = round(value)
    if abs(value - nearest) > 1e-9:
        raise ValidationError(
            field, f"{field} must be a whole number, got {raw.strip()}"
        )
    return int(nearest)


# --------------------------------------------------------------------------
# Pure calculations (deterministic dicts; rendering happens later)
# --------------------------------------------------------------------------


def segments_for(length_ft: float, spacing_ft: float) -> int:
    """Whole number of equal post segments that best fits a run (nearest fit)."""
    if spacing_ft <= 0:
        raise ValidationError("spacing", "spacing must be a positive number")
    return max(1, int(math.floor(length_ft / spacing_ft + 0.5)))


def compute_layout(length_ft: float, width_ft: float, spacing_ft: float) -> dict[str, Any]:
    """Four compass-named runs plus a corner-deduplicated post count."""
    segments_length = segments_for(length_ft, spacing_ft)
    segments_width = segments_for(width_ft, spacing_ft)
    runs = [
        {
            "name": "North",
            "start_corner": "NW",
            "end_corner": "NE",
            "length_ft": length_ft,
            "segments": segments_length,
        },
        {
            "name": "East",
            "start_corner": "NE",
            "end_corner": "SE",
            "length_ft": width_ft,
            "segments": segments_width,
        },
        {
            "name": "South",
            "start_corner": "SE",
            "end_corner": "SW",
            "length_ft": length_ft,
            "segments": segments_length,
        },
        {
            "name": "West",
            "start_corner": "SW",
            "end_corner": "NW",
            "length_ft": width_ft,
            "segments": segments_width,
        },
    ]
    run_end_posts = 2 * (segments_length + 1) + 2 * (segments_width + 1)
    total_posts = 2 * (segments_length + segments_width)
    return {
        "length_ft": length_ft,
        "width_ft": width_ft,
        "spacing_ft": spacing_ft,
        "runs": runs,
        "run_lengths_ft": [run["length_ft"] for run in runs],
        "perimeter_ft": 2 * (length_ft + width_ft),
        "segments_length": segments_length,
        "segments_width": segments_width,
        "run_end_posts": run_end_posts,
        "total_posts": total_posts,
        "post_note": (
            f"{count(run_end_posts)} run-end posts minus the 4 shared corners, "
            "counted once"
        ),
    }


def compute_spacing(run_length_ft: float, requested_spacing_ft: float) -> dict[str, Any]:
    """Fit a whole number of equal segments to one run so the line ends on a post."""
    segments = segments_for(run_length_ft, requested_spacing_ft)
    actual_spacing_ft = round(run_length_ft / segments, 2)
    return {
        "run_length_ft": run_length_ft,
        "requested_spacing_ft": requested_spacing_ft,
        "segments": segments,
        "actual_spacing_ft": actual_spacing_ft,
        "delta_ft": round(actual_spacing_ft - requested_spacing_ft, 2),
        "posts_on_run": segments + 1,
    }


CHECKLIST_ITEMS = (
    ("Corner clearance", "gate sits clear of the corner posts and their braces"),
    ("Flat ground", "ground is level and firm across the whole opening"),
    ("Access side", "gate faces the yard, track or road you drive in from"),
)


def compute_checklist(gate_count: int, gate_width_ft: float) -> dict[str, Any]:
    """Numbered gate openings plus the three named placement checks."""
    listed = [
        {"index": index, "label": f"Gate {index}", "width_ft": gate_width_ft}
        for index in range(1, min(gate_count, MAX_LISTED_GATES) + 1)
    ]
    return {
        "gate_count": gate_count,
        "gate_width_ft": gate_width_ft,
        "total_opening_ft": round(gate_count * gate_width_ft, 2),
        "listed_gates": listed,
        "hidden_gates": max(0, gate_count - MAX_LISTED_GATES),
        "items": [
            {"label": label, "box": "[ ]", "hint": hint}
            for label, hint in CHECKLIST_ITEMS
        ],
    }


# --------------------------------------------------------------------------
# Rendering helpers
# --------------------------------------------------------------------------


def rule_line(widths: list[int]) -> str:
    return "+" + "+".join("-" * (width + 2) for width in widths) + "+"


def table_row(cells: list[str], widths: list[int]) -> str:
    return "|" + "|".join(f" {cell.ljust(width)} " for cell, width in zip(cells, widths)) + "|"


def render_table(headers: list[str], rows: list[list[str]], style: Style) -> list[str]:
    """Aligned monospace columns with ASCII box separators."""
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    lines = [
        style.rule(rule_line(widths)),
        style.accent(table_row(headers, widths)),
        style.rule(rule_line(widths)),
    ]
    lines.extend(table_row(row, widths) for row in rows)
    lines.append(style.rule(rule_line(widths)))
    return lines


def field_line(label: str, value: str, style: Style, width: int = 18) -> str:
    return f"  {label.ljust(width)}{style.accent(value)}"


def render_layout(layout: dict[str, Any], style: Style) -> list[str]:
    rows = [
        [
            run["name"],
            run["start_corner"],
            run["end_corner"],
            f"{feet(run['length_ft'])} ft",
            count(run["segments"]),
        ]
        for run in layout["runs"]
    ]
    rows.append(["Total", "", "", f"{feet(layout['perimeter_ft'])} ft", ""])
    lines = [
        style.accent(f"{PROG} layout"),
        "",
        field_line(
            "Pasture",
            f"{feet(layout['length_ft'])} ft x {feet(layout['width_ft'])} ft",
            style,
        ),
        field_line("Post spacing", f"{feet(layout['spacing_ft'])} ft", style),
        "",
        "Runs",
    ]
    lines.extend(render_table(["Run", "From", "To", "Length", "Segments"], rows, style))
    lines.extend(
        [
            "",
            f"Perimeter: {style.accent(feet(layout['perimeter_ft']) + ' ft')}",
            f"Posts: {style.accent(count(layout['total_posts']))}",
            style.muted(f"  ({layout['post_note']})"),
            "",
            style.muted(
                "Posts per run include both end corners, so buy "
                f"{count(layout['total_posts'])} posts for the loop, not "
                f"{count(layout['run_end_posts'])}."
            ),
        ]
    )
    return lines[:MAX_LINES]


def render_spacing(plan: dict[str, Any], style: Style) -> list[str]:
    return [
        style.accent(f"{PROG} spacing"),
        "",
        field_line("Run length", f"{feet(plan['run_length_ft'])} ft", style),
        field_line("Requested spacing", f"{feet(plan['requested_spacing_ft'])} ft", style),
        "",
        field_line("Equal segments", count(plan["segments"]), style),
        field_line("Even spacing", f"{feet_precise(plan['actual_spacing_ft'])} ft", style),
        field_line("Adjustment", f"{feet_signed(plan['delta_ft'])} ft", style),
        field_line(
            "Posts on this run",
            f"{count(plan['posts_on_run'])}  ({count(plan['segments'])} segments + 1)",
            style,
        ),
        "",
        style.muted(
            "Even spacing is the run length divided by the whole number of segments, "
            "so the run ends on a post with no odd gap."
        ),
    ]


def render_checklist(checklist: dict[str, Any], style: Style) -> list[str]:
    width = feet(checklist["gate_width_ft"])
    lines = [
        style.accent(f"{PROG} checklist"),
        "",
        field_line("Gates", count(checklist["gate_count"]), style),
        field_line("Gate width", f"{width} ft", style),
        "",
        "Gate openings",
    ]
    lines.extend(
        f"  {gate['index']}. Gate {gate['index']} - {width} ft opening"
        for gate in checklist["listed_gates"]
    )
    if checklist["hidden_gates"]:
        first_hidden = checklist["listed_gates"][-1]["index"] + 1
        lines.append(
            style.muted(
                f"  ... {count(checklist['hidden_gates'])} more gates "
                f"({first_hidden}-{count(checklist['gate_count'])}) at {width} ft each"
            )
        )
    lines.extend(
        [
            f"Total opening: {style.accent(feet(checklist['total_opening_ft']) + ' ft')}",
            "",
            "Placement checks - walk the line and tick each box",
        ]
    )
    label_width = max(len(item["label"]) for item in checklist["items"])
    lines.extend(
        f"  {item['label'].ljust(label_width)}   {style.accent(item['box'])}"
        for item in checklist["items"]
    )
    lines.extend(
        [
            "",
            style.muted(
                "Leave a box empty if the gate fails that check and fix the opening "
                "before setting posts."
            ),
        ]
    )
    return lines[:MAX_LINES]


# --------------------------------------------------------------------------
# Usage / help block
# --------------------------------------------------------------------------


def invocation() -> str:
    """How the user actually typed the program (python file, or installed script)."""
    program = os.path.basename(sys.argv[0] or "")
    if program.endswith(".py"):
        return f"python {program}"
    return program or PROG


def examples() -> dict[str, str]:
    call = invocation()
    return {
        "layout": f"{call} layout --length 100 --width 50 --spacing 10",
        "spacing": f"{call} spacing --run 100 --spacing 12",
        "checklist": f"{call} checklist --gates 2 --gate-width 12",
    }


def render_usage_block(style: Style = PLAIN) -> list[str]:
    call = invocation()
    commands = examples()
    return [
        style.accent(f"{PROG} {__version__} - rectangular horse-pasture fence layout"),
        "",
        "Usage",
        f"  {call} layout    --length FT --width FT --spacing FT",
        f"  {call} spacing   --run FT --spacing FT",
        f"  {call} checklist --gates N --gate-width FT",
        f"  {call} --help | --version",
        "",
        "Commands",
        "  layout     Four compass-named runs, perimeter and a corner-deduplicated post count.",
        "  spacing    Fit a whole number of equal post segments to one run.",
        "  checklist  Numbered gate openings plus the corner-clearance, flat-ground",
        "             and access-side placement checks.",
        "",
        "Examples",
        f"  {commands['layout']}",
        f"  {commands['spacing']}",
        f"  {commands['checklist']}",
        "",
        f"Add {style.accent('--json')} to any command for machine-readable output.",
        f"{style.muted('Feet only. No files written, no network used, no configuration needed.')}",
    ]


def subcommand_epilog(command: str) -> str:
    call = examples()[command]
    return (
        "Example\n"
        f"  {call}\n\n"
        "Add --json for machine-readable output. Feet only; nothing is written to disk."
    )


# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------


class CliParser(argparse.ArgumentParser):
    """argparse parser that reports usage problems instead of exiting itself."""

    def __init__(self, *args: Any, example: str | None = None, **kwargs: Any) -> None:
        self.example = example
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> Any:  # type: ignore[override]
        raise UsageError(message, example=self.example)


def build_parser() -> CliParser:
    parser = CliParser(
        prog=invocation(),
        description=f"{PROG} - rectangular horse-pasture fence layout (feet only).",
        add_help=False,
    )
    parser.add_argument("-h", "--help", action="store_true", help="show this help and exit")
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    layout = subparsers.add_parser(
        "layout",
        help="four runs, perimeter and a corner-deduplicated post count",
        description=(
            "Lay out a rectangular pasture: four compass-named runs, the total "
            "perimeter and the post count for the loop (shared corners counted once)."
        ),
        epilog=subcommand_epilog("layout"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        example=examples()["layout"],
    )
    layout.add_argument("--length", metavar="FT", help="pasture length in feet (north/south runs)")
    layout.add_argument("--width", metavar="FT", help="pasture width in feet (east/west runs)")
    layout.add_argument("--spacing", metavar="FT", help="post spacing in feet")
    layout.add_argument("--json", action="store_true", help="print the layout as JSON")
    layout.add_argument("--no-color", action="store_true", help="disable colour output")

    spacing = subparsers.add_parser(
        "spacing",
        help="fit equal post segments to one run",
        description=(
            "Fit a whole number of equal post segments to a single run, so the fence "
            "line ends on a post with no odd gap at the far end."
        ),
        epilog=subcommand_epilog("spacing"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        example=examples()["spacing"],
    )
    spacing.add_argument("--run", metavar="FT", help="run length in feet")
    spacing.add_argument("--spacing", metavar="FT", help="requested post spacing in feet")
    spacing.add_argument("--json", action="store_true", help="print the plan as JSON")
    spacing.add_argument("--no-color", action="store_true", help="disable colour output")

    checklist = subparsers.add_parser(
        "checklist",
        help="numbered gate openings plus the three placement checks",
        description=(
            "Print a walk-the-line gate checklist sized to the number of gates and the "
            "gate width you enter: numbered openings, total opening feet, then the three "
            "placement checks with an empty [ ] box each."
        ),
        epilog=subcommand_epilog("checklist"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        example=examples()["checklist"],
    )
    checklist.add_argument("--gates", metavar="N", help="number of gates (whole number)")
    checklist.add_argument("--gate-width", metavar="FT", help="gate opening width in feet")
    checklist.add_argument("--json", action="store_true", help="print the checklist as JSON")
    checklist.add_argument("--no-color", action="store_true", help="disable colour output")

    return parser


# --------------------------------------------------------------------------
# Command implementations
# --------------------------------------------------------------------------


def run_layout(args: argparse.Namespace, style: Style) -> int:
    length_ft = positive_float("length", args.length, "--length")
    width_ft = positive_float("width", args.width, "--width")
    spacing_ft = positive_float("spacing", args.spacing, "--spacing")
    layout = compute_layout(length_ft, width_ft, spacing_ft)
    if args.json:
        print(json.dumps(layout, indent=2))
        return 0
    print("\n".join(render_layout(layout, style)))
    return 0


def run_spacing(args: argparse.Namespace, style: Style) -> int:
    run_length_ft = positive_float("run", args.run, "--run")
    requested_spacing_ft = positive_float("spacing", args.spacing, "--spacing")
    plan = compute_spacing(run_length_ft, requested_spacing_ft)
    if args.json:
        print(json.dumps(plan, indent=2))
        return 0
    print("\n".join(render_spacing(plan, style)))
    return 0


def run_checklist(args: argparse.Namespace, style: Style) -> int:
    gate_count = positive_count("gate count", args.gates, "--gates")
    gate_width_ft = positive_float("gate width", args.gate_width, "--gate-width")
    checklist = compute_checklist(gate_count, gate_width_ft)
    if args.json:
        print(json.dumps(checklist, indent=2))
        return 0
    print("\n".join(render_checklist(checklist, style)))
    return 0


HANDLERS = {
    "layout": run_layout,
    "spacing": run_spacing,
    "checklist": run_checklist,
}


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    style = Style(enabled=colour_enabled(sys.stdout))

    if not argv:
        # Bare invocation: state the problem, print the usage block, exit 2.
        print("\n".join([f"{PROG}: no subcommand given", ""] + render_usage_block(style)))
        print(
            f"error: no subcommand given - try `{examples()['layout']}`",
            file=sys.stderr,
        )
        return 2

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except UsageError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        if exc.example:
            print(f"Example: {exc.example}", file=sys.stderr)
        else:
            print("", file=sys.stderr)
            print("\n".join(render_usage_block(PLAIN)), file=sys.stderr)
        return 2

    if getattr(args, "help", False):
        print("\n".join(render_usage_block(style)))
        return 0

    if getattr(args, "no_color", False):
        style = PLAIN

    handler = HANDLERS.get(args.command)
    if handler is None:
        print("\n".join([f"{PROG}: no subcommand given", ""] + render_usage_block(style)))
        print(
            f"error: no subcommand given - try `{examples()['layout']}`",
            file=sys.stderr,
        )
        return 2

    try:
        return handler(args, style)
    except ValidationError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        print(f"Example: {examples()[args.command]}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
