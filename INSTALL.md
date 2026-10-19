# Installing EquestrianFence

EquestrianFence is one Python file that uses only the standard library. You can
run it with nothing installed at all:

```bash
python3 equestrian_fence.py --help
```

`install.sh` is optional convenience: it installs the test runner (`pytest`) and
puts the `equestrianfence` console script on your `PATH`. It never installs
system packages, never needs `sudo`, and it exits when it is done — it does not
start anything in the foreground.

## Prerequisites (installed by you, not by the script)

| Requirement | Notes |
|---|---|
| Python 3.9 or newer | 3.11 is what this project is developed and tested on. `python3 --version` |
| pip | Only needed for the optional `install.sh` step and for running the test suite. |
| A terminal | Any POSIX shell. No display, no browser, no database. |

Nothing else: no C compiler, no system libraries, no database server, no
network access at runtime.

## 1. Get the files

Copy or clone the folder and change into it:

```bash
cd equestrianfence
```

## 2. Install (optional but recommended) — one command, then it exits

```bash
bash install.sh
```

What it does, in order:

1. `pip install --upgrade pip setuptools wheel` (tooling first).
2. `pip install -r requirements.txt` — the test runner only. The tool itself has
   no third-party dependencies.
3. `pip install -e .` — installs the `equestrianfence` console script from
   `pyproject.toml`.
4. A self-check: imports the module and runs one `layout` command.

It is idempotent — re-run it any time. To do the same steps by hand:

```bash
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

## 3. Verify the install

```bash
python3 equestrian_fence.py --version
python3 equestrian_fence.py layout --length 100 --width 50 --spacing 10
```

Expect `Posts: 30` and `Perimeter: 300 ft`.

## 4. Run it

```bash
python3 equestrian_fence.py --help
# or the console script installed in step 2:
equestrianfence --help
```

There is no server to start, no `PORT`, no database to migrate and no seed step:
the tool reads its arguments, prints an answer and exits. Nothing is written to
disk.

## 5. See the whole tool at once

```bash
bash demo.sh
```

It never prompts: it walks layout, spacing, the gate checklist, a rejected input
and the JSON output, runs to completion unattended, and exits `0`.

## 6. Run the tests

```bash
python3 -m pytest -q
```

The suite runs every subcommand as a real subprocess, asserts exit codes and
stream routing, checks the no-traceback promise on every error path, and verifies
that a demo run writes no files. No network, no fixtures, no prompts.

## Uninstall

```bash
python3 -m pip uninstall equestrianfence
```

Nothing else was added to your machine; the tool itself is the file
`equestrian_fence.py`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `equestrianfence: command not found` | `install.sh` was not run, or pip's script directory is not on `PATH`. Use `python3 equestrian_fence.py` instead. |
| `pip install -e .` fails on an old pip | Run `python3 -m pip install --upgrade pip setuptools wheel` first — that is the first line of `install.sh`. |
| Coloured text in a piped file | Colour is off whenever stdout is not a terminal. If your terminal environment forces it, pass `--no-color` or set `NO_COLOR=1`. |
| `ModuleNotFoundError: pytest` | `python3 -m pip install -r requirements.txt` (only needed for the test suite, not for the tool). |
