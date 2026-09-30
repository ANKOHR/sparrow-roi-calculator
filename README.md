# Sparrow ROI Calculator

No baseline, no number. Hypotheticals stay labelled.

Sparrow's local Python CLI quantifies automation savings from recorded discovery
measurements. Runtime dependencies are Python standard library only. No network,
GPU packages, or language-model calls are used. Python 3.10 or newer is required.

## Quickstart

Install locally using available setuptools, without accessing the network:

```powershell
python -m pip install --no-deps --no-build-isolation -e .
src fixtures --out demo --store demo/baselines.json
src baseline --store demo/baselines.json --process "invoice data entry" --minutes-per-run 45 --runs-per-week 5 --hourly-rate 30 --notes "measured on discovery call" --observed-by "Henry Williams" --update
src model --store demo/baselines.json --process "invoice data entry" --automation "CSV import script" --minutes-per-run 5
src model --store demo/baselines.json --process "missing process" --automation "script" --minutes-per-run 5
src scenario --hypothetical --process "supplier onboarding" --minutes-per-run 45 --runs-per-week 5 --automation "portal form" --new-minutes-per-run 5 --hourly-rate 30
src actual --store demo/baselines.json --process "invoice data entry" --minutes-per-run 6 --notes "measured one month post-build"
src report --store demo/baselines.json --format md --out demo/roi.md
python -m pytest -q
```

The missing-process command intentionally exits nonzero. The fixture already
contains invoice data entry, so this demo uses --update. For a new store omit it.
`python -m roicalc` is equivalent to the installed `src` command. pytest is a
development tool, not a runtime dependency.

## Architecture

```text
recorded measurements -> JSON store -> model -> report (md or json)
post-build actuals -------------> store ------> predicted vs actual
hypothetical inputs -> scenario -> labelled stdout (no store access)
synthetic fixtures -> labelled store examples -> report hypothetical section
```

The package is roicalc; the console command is src. The default store is
./.src-baselines.json. --store PATH works before or after the subcommand.
Each model loads the store fresh and retains its own baseline snapshot and
automation description. Updating a baseline never rewrites old predictions.
Reports include current baseline provenance and the provenance of each snapshot.
Actual savings are calculated against each prediction's baseline for comparison.

## HONESTY BOUNDARY

Time saved in measured models is computed ONLY from recorded measured baselines.
Without a baseline the model raises BaselineMissingError, exits nonzero, and
writes nothing. Exact process matching is required, including case. No fuzzy
lookup or estimation is performed. Hypothetical scenarios require --hypothetical,
never read or write the store, and always carry the header HYPOTHETICAL SCENARIO -
NOT BASED ON MEASURED DATA. Money is computed only from a recorded positive hourly
rate; otherwise the money section is omitted with the note "no hourly rate
recorded; time savings only". Synthetic fixtures are labelled fictional data.
Measured and hypothetical report sections are separate; there are no mixed totals.

Known limitation: a human can hand-edit a baseline to an unmeasured number.
Schema validation cannot establish whether a measurement happened. observed_by,
observed_date, and notes are always present and shown so readers can assess the
source. If an observer was omitted, observed_by says "not supplied"; recording it
and informative notes is strongly encouraged. observed_date is the UTC ISO
recording timestamp. Reports render stored timestamps verbatim, never generate
new timestamps, and preserve model insertion order for byte-identical repeats.

## Formula reference

All inputs and computation use Decimal, with 50-digit calculation precision.
Money is quantized once at display to 0.01 with ROUND_HALF_UP, in GBP. JSON money
is a string with exactly two decimal places. JSON time retains high precision as
decimal strings for auditability; Markdown time shows minutes and hours to one
decimal with ROUND_HALF_UP. Money in both formats shares the same computation.

```text
saved minutes/run = baseline minutes/run - automation minutes/run
weekly minutes = saved minutes/run * baseline runs/week
monthly minutes = weekly minutes * 52 / 12
yearly minutes = weekly minutes * 52
hours = minutes / 60
money GBP = hours * recorded hourly rate, quantized to 2dp ROUND_HALF_UP
```

45 to 5 minutes at 5 runs/week yields 200 weekly minutes, 866.67 monthly
minutes when checked to 2dp, and 10400 yearly minutes. At GBP 30/hour this is
100.00 weekly, 433.33 monthly, and 5200.00 yearly. Zero and negative savings are
shown with "automation not faster than manual". Baseline minutes, runs, and
rates must be positive finite numbers. New and actual minutes may be zero.

## CLI reference

| Command | Arguments and behavior |
| --- | --- |
| baseline | --process NAME --minutes-per-run N --runs-per-week N [--hourly-rate N] [--notes TEXT] [--observed-by NAME] [--update]. Records provenance; updates include a replaced-at note. |
| model | --process NAME --automation TEXT --minutes-per-run N. Saves an independent prediction from the fresh baseline. |
| scenario | --hypothetical --process NAME --minutes-per-run N --runs-per-week N --automation TEXT --new-minutes-per-run N [--hourly-rate N]. Prints labelled computation without store access. |
| actual | --process NAME --minutes-per-run N [--notes TEXT]. Records the latest post-build observation for a baseline. |
| report | --format md or json [--process NAME] [--out FILE]. Renders models, provenance, actuals, and fixture hypothetical examples. Defaults to md and stdout. |
| fixtures | --out DIR [--store PATH]. Writes deterministic synthetic baselines.json plus roi.md and roi.json. Explicit --store selects the store location. |

Every command accepts --store PATH. A scenario ignores it. Live scenarios are
ephemeral stdout results and do not appear in later reports: persisting them
would violate the no-store-write rule. Reports can show explicitly labelled
hypothetical examples supplied by the synthetic fixture generator.

## Error catalogue

| Named error | Trigger |
| --- | --- |
| ValidationError | Empty process or automation; malformed, infinite, negative, or disallowed zero numeric input. |
| DuplicateBaselineError | Existing exact process name without --update. |
| BaselineMissingError | Model or actual requests a process without a recorded baseline; suggests src baseline. |
| StoreCorruptError | Invalid JSON or invalid store schema; original file remains unchanged. |
| StoreIOError | Store or report filesystem access fails, including atomic replacement failure. |

CLI errors print the name and message to stderr with exit code 1, without a
traceback. argparse usage errors exit 2, including missing --hypothetical.
Store writes use a sibling temporary file, flush/fsync, and atomic os.replace;
failed replacement leaves the original untouched and cleans up the temporary.
Atomic replacement prevents partially written JSON, but concurrent writers can
lose one another's updates. Use one writer at a time; this is a local sales tool,
not a multi-user database. Store version 1 holds baselines, models, actuals,
hypotheticals, and a synthetic marker. Numeric fields are decimal strings.

## Fixtures and evidence loop

The fictional Finch Office fixture has invoice data entry (45 minutes, 5 runs,
GBP 30/hour), weekly filing (20 minutes, 2 runs, no rate), two model examples,
an actual invoice measurement of 6 minutes, and hypothetical supplier onboarding.
It uses fixed timestamps and no randomness. Repeated generation produces
byte-identical files. Fixtures overwrite the chosen fixture store deliberately;
use a dedicated demo directory, never a live measurements store.

After shipping an automation record its measured actual minutes. Reports compare
predicted and actual minutes, hours, and money side by side. After the first three
real actuals, check for systematic optimism. If present, adjust modelling guidance
to require conservative and optimistic cases, using separate model commands.

Maintain as Sparrow sales tooling. Integrate Audit Generator findings into
baseline recording and feed defensible savings into Proposal Builder pricing.
Commercialise within Sparrow discovery, not as a standalone product. Kill only
if real engagements consistently refuse measurements. The KOML lesson is to
refuse computation without measurements and provide the exact missing-input
command instead of computing with a caveat.
