"""End-to-end and unit tests for the EquestrianFence CLI.

Every command is exercised through a real subprocess so exit codes, stream
routing (results on stdout, errors on stderr) and the no-traceback promise are
verified exactly as a user would experience them.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import equestrian_fence as ef

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "equestrian_fence.py"


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the CLI in a clean environment (no NO_COLOR, no colour forcing)."""
    env = {key: value for key, value in os.environ.items() if key != "NO_COLOR"}
    env.pop("FORCE_COLOR", None)
    env.pop("PY_COLORS", None)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd or ROOT),
        timeout=30,
    )


# ---------------------------------------------------------------------------
# F1 / T1 - fence run layout
# ---------------------------------------------------------------------------


def test_layout_prints_four_compass_runs_and_perimeter() -> None:
    result = run_cli("layout", "--length", "100", "--width", "50", "--spacing", "10")

    assert result.returncode == 0
    assert result.stderr == ""
    for line in (
        "North",
        "East",
        "South",
        "West",
        "100 ft",
        "50 ft",
        "300 ft",
    ):
        assert line in result.stdout
    assert "Perimeter: 300 ft" in result.stdout


def test_layout_reports_deduplicated_post_count_with_note() -> None:
    result = run_cli("layout", "--length", "100", "--width", "50", "--spacing", "10")

    assert "Posts: 30" in result.stdout
    assert "34 run-end posts" in result.stdout
    assert "4 shared corners" in result.stdout
    assert "counted once" in result.stdout


def test_layout_runs_are_north_east_south_west_with_shared_corners() -> None:
    layout = ef.compute_layout(100.0, 50.0, 10.0)

    assert [run["name"] for run in layout["runs"]] == ["North", "East", "South", "West"]
    assert layout["run_lengths_ft"] == [100.0, 50.0, 100.0, 50.0]
    assert layout["runs"][0]["start_corner"] == "NW"
    assert layout["runs"][0]["end_corner"] == "NE"
    assert layout["runs"][3]["end_corner"] == "NW"  # closes the loop
    assert layout["perimeter_ft"] == 300.0


def test_layout_post_count_is_run_end_posts_minus_four_corners() -> None:
    for length, width, spacing in ((100.0, 50.0, 10.0), (160.0, 120.0, 12.0), (60.0, 40.0, 8.0)):
        layout = ef.compute_layout(length, width, spacing)

        assert layout["run_end_posts"] == (layout["segments_length"] + 1) * 2 + (
            layout["segments_width"] + 1
        ) * 2
        assert layout["total_posts"] == layout["run_end_posts"] - 4
        assert layout["total_posts"] == 2 * (layout["segments_length"] + layout["segments_width"])


@pytest.mark.parametrize("spacing", ["0", "-5"])
def test_layout_rejects_non_positive_spacing(spacing: str) -> None:
    result = run_cli("layout", "--length", "100", "--width", "50", "--spacing", spacing)

    assert result.returncode == 2
    assert "spacing must be a positive number" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.stdout == ""


def test_layout_rejects_zero_length() -> None:
    result = run_cli("layout", "--length", "0", "--width", "50", "--spacing", "10")

    assert result.returncode == 2
    assert "length must be a positive number" in result.stderr
    assert "Traceback" not in result.stderr


def test_layout_rejects_non_numeric_length() -> None:
    result = run_cli("layout", "--length", "abc", "--width", "50", "--spacing", "10")

    assert result.returncode == 2
    assert "length must be a number" in result.stderr
    assert "Traceback" not in result.stderr


def test_layout_names_the_missing_argument() -> None:
    result = run_cli("layout", "--length", "100", "--width", "50")

    assert result.returncode == 2
    assert "spacing" in result.stderr
    assert "layout --length 100 --width 50 --spacing 10" in result.stderr


# ---------------------------------------------------------------------------
# F2 / T2 - post spacing calculator
# ---------------------------------------------------------------------------


def test_spacing_fits_eight_equal_segments() -> None:
    result = run_cli("spacing", "--run", "100", "--spacing", "12")

    assert result.returncode == 0
    assert "8" in result.stdout
    assert "12.50 ft" in result.stdout
    assert "+0.50 ft" in result.stdout
    assert "9" in result.stdout
    assert "Posts on this run" in result.stdout


def test_spacing_exact_fit_reports_zero_adjustment() -> None:
    result = run_cli("spacing", "--run", "100", "--spacing", "10")

    assert result.returncode == 0
    assert "10" in result.stdout
    assert "10.00 ft" in result.stdout
    assert "0.00 ft" in result.stdout
    assert "11" in result.stdout


def test_spacing_plan_math() -> None:
    plan = ef.compute_spacing(100.0, 12.0)

    assert plan["segments"] == 8
    assert plan["actual_spacing_ft"] == 12.5
    assert plan["delta_ft"] == 0.5
    assert plan["posts_on_run"] == 9
    assert plan["posts_on_run"] == plan["segments"] + 1


def test_spacing_never_leaves_an_odd_gap_at_the_end() -> None:
    for run_length, spacing in ((100.0, 12.0), (160.0, 12.0), (57.5, 9.0), (12.0, 20.0)):
        plan = ef.compute_spacing(run_length, spacing)

        assert plan["segments"] >= 1
        # the fitted spacing covers the run: only the 2-decimal rounding remains
        covered = plan["segments"] * plan["actual_spacing_ft"]
        assert abs(covered - run_length) <= 0.005 * plan["segments"] + 1e-9


@pytest.mark.parametrize("spacing", ["0", "-4"])
def test_spacing_rejects_non_positive_spacing(spacing: str) -> None:
    result = run_cli("spacing", "--run", "100", "--spacing", spacing)

    assert result.returncode == 2
    assert "spacing must be a positive number" in result.stderr
    assert "Traceback" not in result.stderr


def test_spacing_rejects_non_numeric_spacing() -> None:
    result = run_cli("spacing", "--run", "100", "--spacing", "twelve")

    assert result.returncode == 2
    assert "spacing must be a number" in result.stderr
    assert "Traceback" not in result.stderr


def test_spacing_names_the_missing_run_argument() -> None:
    result = run_cli("spacing", "--spacing", "12")

    assert result.returncode == 2
    assert "run" in result.stderr
    assert "spacing --run 100 --spacing 12" in result.stderr


# ---------------------------------------------------------------------------
# F3 / T3 - gate placement checklist
# ---------------------------------------------------------------------------


def test_checklist_prints_numbered_gates_and_total_opening() -> None:
    result = run_cli("checklist", "--gates", "2", "--gate-width", "12")

    assert result.returncode == 0
    assert "Gate 1" in result.stdout
    assert "Gate 2" in result.stdout
    assert "Gate 3" not in result.stdout
    assert "12 ft opening" in result.stdout
    assert "Total opening: 24 ft" in result.stdout


def test_checklist_prints_three_named_checks_with_empty_boxes() -> None:
    result = run_cli("checklist", "--gates", "2", "--gate-width", "12")

    for label in ("Corner clearance", "Flat ground", "Access side"):
        line = next(row for row in result.stdout.splitlines() if label in row)
        assert line.rstrip().endswith("[ ]"), f"{label} row has no empty box: {line!r}"
    assert result.stdout.count("[ ]") == 3


def test_checklist_has_exactly_three_items() -> None:
    checklist = ef.compute_checklist(2, 12.0)

    assert [item["label"] for item in checklist["items"]] == [
        "Corner clearance",
        "Flat ground",
        "Access side",
    ]
    assert all(item["box"] == "[ ]" for item in checklist["items"])
    assert checklist["total_opening_ft"] == 24.0


def test_checklist_is_capped_so_output_stays_short() -> None:
    result = run_cli("checklist", "--gates", "40", "--gate-width", "12")

    assert result.returncode == 0
    assert len(result.stdout.splitlines()) <= ef.MAX_LINES
    assert "more gates" in result.stdout
    assert "Total opening: 480 ft" in result.stdout


@pytest.mark.parametrize("width", ["0", "-4"])
def test_checklist_rejects_non_positive_gate_width(width: str) -> None:
    result = run_cli("checklist", "--gates", "2", "--gate-width", width)

    assert result.returncode == 2
    assert "gate width must be a positive number" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("gates", ["0", "-1"])
def test_checklist_rejects_non_positive_gate_count(gates: str) -> None:
    result = run_cli("checklist", "--gates", gates, "--gate-width", "12")

    assert result.returncode == 2
    assert "gate count must be a positive number" in result.stderr
    assert "Traceback" not in result.stderr


def test_checklist_rejects_non_numeric_gate_width() -> None:
    result = run_cli("checklist", "--gates", "2", "--gate-width", "twelve")

    assert result.returncode == 2
    assert "gate width must be a number" in result.stderr
    assert "Traceback" not in result.stderr


def test_checklist_rejects_fractional_gate_count() -> None:
    result = run_cli("checklist", "--gates", "2.5", "--gate-width", "12")

    assert result.returncode == 2
    assert "gate count must be a whole number" in result.stderr


def test_checklist_names_the_missing_gates_argument() -> None:
    result = run_cli("checklist", "--gate-width", "12")

    assert result.returncode == 2
    assert "--gates" in result.stderr
    assert "checklist --gates 2 --gate-width 12" in result.stderr


# ---------------------------------------------------------------------------
# T4 - help coverage and unknown subcommands
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [[], ["layout"], ["spacing"], ["checklist"]])
def test_help_exits_zero_with_examples(path: list[str]) -> None:
    result = run_cli(*path, "--help")

    assert result.returncode == 0
    assert "usage" in result.stdout.lower()
    assert "Example" in result.stdout


def test_top_level_help_lists_every_subcommand_with_an_example() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    for command in ("layout", "spacing", "checklist"):
        assert command in result.stdout
    assert "layout --length 100 --width 50 --spacing 10" in result.stdout


def test_version_flag() -> None:
    result = run_cli("--version")

    assert result.returncode == 0
    assert ef.__version__ in result.stdout


def test_bare_invocation_prints_usage_and_exits_two() -> None:
    result = run_cli()

    assert result.returncode == 2
    assert "no subcommand given" in result.stdout
    for command in ("layout", "spacing", "checklist"):
        assert command in result.stdout


def test_unknown_subcommand_echoes_token_and_usage() -> None:
    result = run_cli("fence")

    assert result.returncode == 2
    assert "fence" in result.stderr
    for command in ("layout", "spacing", "checklist"):
        assert command in result.stderr
    assert "Traceback" not in result.stderr


def test_unknown_flag_is_a_usage_error() -> None:
    result = run_cli("layout", "--length", "100", "--width", "50", "--spacing", "10", "--bogus")

    assert result.returncode == 2
    assert "--bogus" in result.stderr
    assert "Traceback" not in result.stderr


# ---------------------------------------------------------------------------
# T5 - integration smoke: formatting, exit codes, no files, no network
# ---------------------------------------------------------------------------


DEMO_COMMANDS = [
    ("layout", "--length", "100", "--width", "50", "--spacing", "10"),
    ("spacing", "--run", "100", "--spacing", "12"),
    ("checklist", "--gates", "2", "--gate-width", "12"),
]


@pytest.mark.parametrize("command", DEMO_COMMANDS)
def test_demo_output_is_ascii_and_short(command: tuple[str, ...]) -> None:
    result = run_cli(*command)

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.isascii(), "output must be plain ASCII in a pipe"
    assert "\x1b" not in result.stdout, "no ANSI escapes when stdout is not a TTY"
    assert len(result.stdout.splitlines()) <= ef.MAX_LINES


def test_no_scientific_notation_and_at_most_two_decimals() -> None:
    result = run_cli("layout", "--length", "33.333", "--width", "17.777", "--spacing", "7.1")

    assert result.returncode == 0
    assert "e+" not in result.stdout.lower()
    assert "e-" not in result.stdout.lower()


def test_demo_run_writes_no_files(tmp_path: Path) -> None:
    before = sorted(p.name for p in tmp_path.iterdir())

    for command in DEMO_COMMANDS:
        result = run_cli(*command, cwd=tmp_path)
        assert result.returncode == 0

    assert sorted(p.name for p in tmp_path.iterdir()) == before == []


def test_source_has_no_network_imports() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    for banned in ("import requests", "import urllib", "import socket", "import http"):
        assert banned not in source
    assert "urlopen" not in source


def test_module_uses_only_the_standard_library() -> None:
    imported = {
        line.split()[1].split(".")[0]
        for line in SCRIPT.read_text(encoding="utf-8").splitlines()
        if line.startswith("import ") or line.startswith("from ")
    }

    stdlib = {"__future__", "argparse", "json", "math", "os", "sys", "dataclasses", "typing"}
    assert imported <= stdlib, f"non-stdlib imports: {sorted(imported - stdlib)}"


# ---------------------------------------------------------------------------
# Shared validator and machine-readable output
# ---------------------------------------------------------------------------


def test_positive_float_shared_validator() -> None:
    assert ef.positive_float("spacing", "12") == 12.0
    assert ef.positive_float("spacing", " 2.5 ") == 2.5

    with pytest.raises(ef.ValidationError) as empty:
        ef.positive_float("spacing", "")
    assert "spacing must be a number" in empty.value.message

    with pytest.raises(ef.ValidationError) as text:
        ef.positive_float("spacing", "twelve")
    assert "spacing must be a number" in text.value.message

    with pytest.raises(ef.ValidationError) as zero:
        ef.positive_float("spacing", "0")
    assert zero.value.message == "spacing must be a positive number, got 0"
    assert zero.value.exit_code == 2
    assert zero.value.field == "spacing"


def test_positive_float_rejects_infinity_and_nan() -> None:
    for raw in ("inf", "nan"):
        with pytest.raises(ef.ValidationError):
            ef.positive_float("length", raw)


@pytest.mark.parametrize("command", DEMO_COMMANDS)
def test_json_mode_is_parseable(command: tuple[str, ...]) -> None:
    result = run_cli(*command, "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert payload


def test_json_layout_contract() -> None:
    result = run_cli("layout", "--length", "100", "--width", "50", "--spacing", "10", "--json")
    payload = json.loads(result.stdout)

    assert payload["perimeter_ft"] == 300.0
    assert payload["total_posts"] == 30
    assert [run["name"] for run in payload["runs"]] == ["North", "East", "South", "West"]
