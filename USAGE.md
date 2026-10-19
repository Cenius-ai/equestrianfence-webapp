# Using EquestrianFence

Three subcommands, one unit (feet), one rectangle. Every command prints its
answer to stdout, exits `0`, and writes nothing to disk.

```bash
python3 equestrian_fence.py --help
python3 equestrian_fence.py layout    --length 100 --width 50  --spacing 10
python3 equestrian_fence.py spacing   --run 100    --spacing 12
python3 equestrian_fence.py checklist --gates 2    --gate-width 12
```

After `bash install.sh` you can drop `python3 equestrian_fence.py` for the
console script: `equestrianfence layout --length 100 --width 50 --spacing 10`.

---

## 1. Fence run layout — `layout`

> "I have a 100 × 50 ft paddock and posts every 10 ft. How many runs, how much
> perimeter, how many posts do I buy?"

```bash
python3 equestrian_fence.py layout --length 100 --width 50 --spacing 10
```

```
equestrianfence layout

  Pasture           100 ft x 50 ft
  Post spacing      10 ft

Runs
+-------+------+----+--------+----------+
| Run   | From | To | Length | Segments |
+-------+------+----+--------+----------+
| North | NW   | NE | 100 ft | 10       |
| East  | NE   | SE | 50 ft  | 5        |
| South | SE   | SW | 100 ft | 10       |
| West  | SW   | NW | 50 ft  | 5        |
| Total |      |    | 300 ft |          |
+-------+------+----+--------+----------+

Perimeter: 300 ft
Posts: 30
  (34 run-end posts minus the 4 shared corners, counted once)

Posts per run include both end corners, so buy 30 posts for the loop, not 34.
```

**The arithmetic, spelled out.**

- Runs: `--length` drives North and South, `--width` drives East and West. Every
  run also prints the corner it starts at and the corner it ends at, so the loop
  closes: `NW → NE → SE → SW → NW`.
- Perimeter = `2 × (length + width)` = `2 × (100 + 50)` = `300 ft`.
- Segments per side = the whole number of equal segments that best fits that
  side: `100 / 10 = 10` and `50 / 10 = 5`.
- Posts on one side = segments + 1 (a post at each end) → 11 and 6.
- **Run-end posts** = `11 + 6 + 11 + 6 = 34`. Every corner is shared by two
  adjacent runs, so that sum counts the four corners twice.
- **Posts to buy** = `34 − 4` = `2 × (segments_length + segments_width)` =
  `2 × (10 + 5)` = **30**.

That last line is the whole point of the command: summing the run-end posts
over-orders by exactly four posts.

---

## 2. Post spacing calculator — `spacing`

> "The north run is 100 ft and I want posts roughly every 12 ft. Where do the
> posts actually land?"

```bash
python3 equestrian_fence.py spacing --run 100 --spacing 12
```

```
equestrianfence spacing

  Run length        100 ft
  Requested spacing 12 ft

  Equal segments    8
  Even spacing      12.50 ft
  Adjustment        +0.50 ft
  Posts on this run 9  (8 segments + 1)

Even spacing is the run length divided by the whole number of segments, so the run ends on a post with no odd gap.
```

**The arithmetic.**

- Segments = the whole number nearest to `run / requested` (at least 1):
  `100 / 12 = 8.33 → 8`.
- Even spacing = `run / segments` rounded to two decimals: `100 / 8 = 12.50 ft`.
- Adjustment = `even spacing − requested`: `12.50 − 12 = +0.50 ft`. A negative
  figure means the posts come out slightly tighter than asked; `0.00` means the
  request fits exactly.
- Posts on the run = `segments + 1` = `9`.

An exact fit needs no adjustment:

```bash
python3 equestrian_fence.py spacing --run 100 --spacing 10
#   Equal segments    10
#   Even spacing      10.00 ft
#   Adjustment        0.00 ft
#   Posts on this run 11  (10 segments + 1)
```

---

## 3. Gate placement checklist — `checklist`

> "Two 12 ft gates. Print me the openings and the things to check on site."

```bash
python3 equestrian_fence.py checklist --gates 2 --gate-width 12
```

```
equestrianfence checklist

  Gates             2
  Gate width        12 ft

Gate openings
  1. Gate 1 - 12 ft opening
  2. Gate 2 - 12 ft opening
Total opening: 24 ft

Placement checks - walk the line and tick each box
  Corner clearance   [ ]
  Flat ground        [ ]
  Access side        [ ]

Leave a box empty if the gate fails that check and fix the opening before setting posts.
```

- One numbered line per gate, each showing the opening width.
- `Total opening = gates × width` = `2 × 12 = 24 ft` — the opening you must keep
  clear of posts.
- Three checks, each with an empty `[ ]` box you tick (or leave empty) on paper:
  **Corner clearance** (the gate sits clear of the corner posts and their
  braces), **Flat ground** (level and firm across the whole opening),
  **Access side** (the gate faces the yard, track or road you drive in from).
- Nothing is saved between runs: the checklist is printed, you walk the line
  with it, and the next run starts blank. Long gate lists are truncated with an
  "n more gates" line so the output stays a screenful; the total always covers
  every gate.

---

## 4. Help, exit codes and machine-readable output

```bash
python3 equestrian_fence.py --help            # usage block + one example per command
python3 equestrian_fence.py layout --help     # arguments for one command
python3 equestrian_fence.py --version
```

| Situation | Exit code | Where the message goes |
|---|---|---|
| Success | `0` | stdout |
| Zero or negative dimension | `2` | stderr — `spacing must be a positive number, got 0` |
| Non-numeric dimension | `2` | stderr — `length must be a number, got 'abc'` |
| Missing argument | `2` | stderr — `gate count must be a number: missing --gates` + example |
| Unknown subcommand | `2` | stderr — echoes the word you typed, then the usage block |
| No arguments at all | `2` | usage block on stdout, one-line hint on stderr |

A user error never prints a Python traceback.

For scripts and spreadsheets, add `--json` to any subcommand:

```bash
python3 equestrian_fence.py layout --length 100 --width 50 --spacing 10 --json
```

```json
{
  "length_ft": 100.0,
  "width_ft": 50.0,
  "spacing_ft": 10.0,
  "runs": [ { "name": "North", "start_corner": "NW", "end_corner": "NE", "length_ft": 100.0, "segments": 10 } ],
  "run_lengths_ft": [100.0, 50.0, 100.0, 50.0],
  "perimeter_ft": 300.0,
  "segments_length": 10,
  "segments_width": 5,
  "run_end_posts": 34,
  "total_posts": 30,
  "post_note": "34 run-end posts minus the 4 shared corners, counted once"
}
```

Colour is on only when stdout is a terminal, and never when `NO_COLOR` is set or
`--no-color` is passed — pipes always receive plain ASCII.

---

## 5. A whole afternoon in four commands

Fencing the back field (160 × 120 ft) on 12 ft spacing, with two 12 ft gates:

```bash
python3 equestrian_fence.py layout    --length 160 --width 120 --spacing 12   # 46 posts, 560 ft perimeter
python3 equestrian_fence.py spacing   --run 160    --spacing 12                # 13 segments at 12.31 ft
python3 equestrian_fence.py spacing   --run 120    --spacing 12                # 10 segments at 12.00 ft
python3 equestrian_fence.py checklist --gates 2    --gate-width 12             # 24 ft of opening
```

More preset pastures with their exact commands: [examples/pastures.md](examples/pastures.md).
