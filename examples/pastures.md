# Preset pastures

Three real-world pasture shapes with the exact commands that lay each one out.
Swap the numbers for your own; nothing here is required reading for the tool.

## 1. Arena paddock next to the barn — 100 × 50 ft, 10 ft spacing

A small turnout paddock fenced with posts every 10 ft.

```bash
python3 equestrian_fence.py layout    --length 100 --width 50 --spacing 10
python3 equestrian_fence.py spacing   --run 100 --spacing 10
python3 equestrian_fence.py spacing   --run 50  --spacing 10
python3 equestrian_fence.py checklist --gates 1 --gate-width 12
```

- Perimeter 300 ft, 30 posts for the loop (34 run-end posts − 4 shared corners).
- Both runs fit an exact 10 ft spacing: no adjustment, 11 and 6 posts per side.
- One 12 ft gate on the barn side.

## 2. Back field — 160 × 120 ft, 12 ft spacing, two gates

The big field shared by three horses, gated at the track and at the barn.

```bash
python3 equestrian_fence.py layout    --length 160 --width 120 --spacing 12
python3 equestrian_fence.py spacing   --run 160 --spacing 12
python3 equestrian_fence.py spacing   --run 120 --spacing 12
python3 equestrian_fence.py checklist --gates 2 --gate-width 12
```

- Perimeter 560 ft, 46 posts for the loop.
- The 160 ft run fits 13 segments at 12.31 ft (+0.31 ft versus the request).
- The 120 ft run fits an exact 10 segments at 12.00 ft.
- Two 12 ft gates: 24 ft of total opening.

## 3. Pony paddock — 60 × 40 ft, 8 ft spacing, one gate

Tight spacing for a small pony paddock where a determined shetland is the
engineer.

```bash
python3 equestrian_fence.py layout    --length 60 --width 40 --spacing 8
python3 equestrian_fence.py spacing   --run 60 --spacing 8
python3 equestrian_fence.py checklist --gates 1 --gate-width 10
```

- Perimeter 200 ft, 26 posts for the loop (30 run-end posts − 4 shared corners).
- The 60 ft run fits 8 segments at 7.50 ft (`60 / 8 = 7.5` rounds up to 8
  segments, so the posts come out 0.50 ft tighter than asked); the 40 ft run
  fits an exact 5 segments at 8.00 ft.
- One 10 ft gate.

## Recording what you measured

The tool writes no files — copy the printed block into your own notes or
estimate sheet, or capture JSON for a spreadsheet:

```bash
python3 equestrian_fence.py layout --length 160 --width 120 --spacing 12 --json > field.json
```
