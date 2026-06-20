# Spec: REPO_STRUCTURE.md rewrite + README fix

**Date:** 2026-05-08
**Status:** Approved (awaiting plan)

## Goal

Re-frame `REPO_STRUCTURE.md` from "documentation of this specific repo" to a
**boilerplate template** for sister/future repos (e.g. BESS model, Sweden
model). Patterns-first: each pattern is named, then its instantiation in
this repo is shown so the reader can see *how the pattern produces the
template artefact* and re-instantiate it elsewhere.

Concurrently, fix `README.md` in this repo (it has unresolved git merge
conflict markers and stale Hydra CLI examples).

## Scope

**In scope:**

- Substantive rewrite of `REPO_STRUCTURE.md` per the section table below.
- Mechanical fix of `README.md` (drop merge-conflict's master-side, fix CLI
  flags).

**Out of scope:**

- Code changes anywhere under `src/`, `config/`, `dockerfiles/`,
  `pyproject.toml`, `.pre-commit-config.yaml`. REPO_STRUCTURE.md *flags*
  these as anti-patterns; it does not fix them.
- Deleting `Code/` (legacy folder) or the empty stub
  `ppa_symmetric_info/` at the repo root.
- Addressing the unfinished `_compute_strike_boundaries` `pass`-body
  method.

## Design driver

`REPO_STRUCTURE.md` is consumed by *future* repos that will not have
`Code/`, the empty stub, the merge conflict, or the specific filenames of
this codebase. So content earns its place by carrying a **portable
porting lesson**, not by being currently true of this repo. Repo-specific
accidents that don't generalise are dropped.

Inside surviving sections, each block follows the shape:

1. Name the pattern.
2. Show its instantiation here (concrete example).
3. The reader can see the pattern → instance mapping and re-apply it.

## Section-by-section changes

### §1 — Top-level layout

- File tree: add `data_postprocessor.py` and `sensitivity_runner.py`
  under `data_ops/`.
- Update the lifecycle phrasing under the tree:
  *"`data_ops/` subpackage owns the data lifecycle: generate → reduce →
  load → postprocess, plus sensitivity sweeps."*
- `main.py` annotation: replace the stale "20-line Hydra entry point —
  instantiates Runner" with a pattern-level annotation:
  *"trivial Hydra entry point — calls `Runner.run()`"*.

### §2 — Pipeline

(a) `main.py` snippet → just `runner.run()` (mirrors current code).

(b) Runner stage list rendered as a **flat** list:
`preprocess_data → load_data → solve_nbs_model → postprocess_data →
visualize_results`. No nested if/else block.

(c) Below the flat list, a separate paragraph names the dispatch pattern
explicitly: *"`Runner.run()` runs `preprocess_data` once, then dispatches
between `single_run()` and `sensitivity_run()` on
`config.sensitivity.type`. This is the same dispatch-on-a-string-field
pattern as §3.3 — applied at the orchestrator level."*

(d) Layer table becomes **4 rows** with `DataPostprocessor` included.
Prose trimmed so each cell describes the layer's responsibility, not
specific filenames:

| Layer | What it owns | What it returns |
|---|---|---|
| `DataPreprocessor` | Generation + reduction, **caching** | Files on disk |
| `DataLoader` | All config + all CSVs → numpy arrays | A "data" object — every scalar and matrix the model needs |
| `ModelNashBargaining` | Build vars/constraints/objective, solve, write solver-output artefacts | Solved model object (variables + status) |
| `DataPostprocessor` | Pull values off the solved model; compute post-solve scalars and per-scenario artefacts | Output CSV(s) under `results/<run_type>/<sim_name>/` |

(e) The bullet *"Sensitivity sweeps mutate `data`, not config"* is
upgraded to the **two-mode rule**:

> *"Sweeps mutate `cfg` when the swept field is a config input (via
> `OmegaConf.merge`, then construct a fresh `DataLoader`); they mutate
> `data` directly when the swept field is a quantity computed inside
> `DataLoader` (no config field exists). The model never sees the
> difference — same `data` object regardless."*

### §3.8 — `_directories`

- Remove the line `self.path_results_csv = self.path_sim / "results.csv"`
  from the example (no longer matches the code; that path is owned by
  `DataPostprocessor`).
- Add `self.path_model_mps = self.path_sim / "model.mps"` and
  `self.path_figures.mkdir(exist_ok=True)` to keep the example
  current.
- Append one cross-reference sentence: *"Output paths from extraction
  live in `DataPostprocessor` (§4.14), not here — `_directories` only
  declares paths owned by the model layer."*

### §4.14 — Result extraction

Rewrite the section to layer **two patterns**:

1. **Structural (primary):** *Post-solve extraction lives in its own
   class, separate from the model. Both single-run and sensitivity
   sweeps reuse the same extraction code.* Show how this repo
   instantiates it (`DataPostprocessor`) and how the sensitivity runner
   imports the same class.

2. **Refinement (secondary):** *Prefer iterating the variable
   namespace so new variables auto-appear in the output.* Note that
   this repo's current implementation uses an explicit `self.scalars =
   {...}` dict; the namespace-iteration form is the variant worth
   porting.

The pattern-name "iter the namespace, write to CSV" survives the
rewrite, even though the current code doesn't use it — because the doc's
job is to teach the right pattern for sister repos, not mirror this
repo's current shape.

### §5.1 — Hydra defaults

- The `config.yaml` snippet drops the obsolete top-level
  `run_sensitivity: false` line.
- A new pattern paragraph below the snippet:

> *"The on/off switch for a sub-feature belongs **inside** that feature's
> config group as a `type:` enum, not as a sibling boolean at the top of
> `config.yaml`. Here, `sensitivity/default.yaml` sets `type: none` for
> the off case; `sensitivity/risk_aversion.yaml` sets
> `type: risk_aversion` plus the sweep parameters. Adding a new sweep is
> one new file in `config/sensitivity/`, not two coupled changes (a new
> file *and* flipping a top-level boolean)."*

### §5.5 — CLI examples

- `python main.py run_sensitivity=true` →
  `python main.py sensitivity=risk_aversion`.

### §8 — Known smells / anti-patterns

**Re-frame the section.** Header changes from "Known smells in *this*
repo (don't copy these)" to **"Anti-patterns to avoid when scaffolding a
new repo"**.

**Keep and generalise:**

- `pyproject.toml` left at cookiecutter defaults
  (`description = "Add your description here"`, missing `authors`).
- Dockerfile still references the previous template's package name (this
  repo: `enlight/`) — generic lesson: grep the dockerfile for the old
  template's name after running cookiecutter; leftover `COPY oldname/
  oldname/` lines silently break the build.
- Dependencies declared in `pyproject.toml` but never wired in
  (`pytest` with no `tests/` directory; `ruff` / `mypy` listed but no
  pre-commit hook for them). Generic lesson: prune deps you don't use,
  or wire them in immediately.
- Pre-commit minimal — no linters/typechecker hooks despite both being in
  `pyproject.toml`.

**Drop:**

- Empty sibling `ppa_symmetric_info/` at the repo root — accident of
  this repo's history; future repos won't have it.
- `default_baselaod` typo — already fixed in this repo, never a portable
  lesson.
- `_compute_strike_boundaries` `pass`-body — drop. The generalised
  version ("don't ship `pass`-body methods on main") is a coding
  anti-pattern, not a scaffolding one, and is too generic to teach
  anything in §8.
- `Code/` legacy folder — repo-specific; future repos won't have it.
- README merge conflict — this-repo accident.

## README fix (separate, mechanical)

- Delete lines 72-158: the unresolved merge-conflict master-side block
  (legacy `Code/` workflow narrative, including the
  `<<<<<<< HEAD` / `=======` / `>>>>>>> master` markers).
- Lines 42-43: replace
  `python main.py run_sensitivity=true sensitivity=risk_aversion`
  examples with `python main.py sensitivity=risk_aversion` (the file
  parameter alone activates the sweep — no boolean flag).

## Verification (spec self-review checklist applied to the rewritten file)

The rewritten `REPO_STRUCTURE.md` is correct iff:

1. Every section names a pattern, then shows its instantiation here,
   with the pattern → instance mapping legible.
2. No reference to `Code/`, the legacy stub at the repo root, or the
   README merge conflict appears outside §8 — and §8 only if the lesson
   is generalised.
3. No mention of a `run_sensitivity` flag anywhere in the doc.
4. No claim contradicted by the actual code (specifically: no
   `path_results_csv`, no "20-line main.py" annotation, no missing
   `data_postprocessor.py` / `sensitivity_runner.py` from the file
   tree).
5. CLI examples in §5.5 match the `config.sensitivity.type` dispatch.
6. README.md has no merge-conflict markers and no `run_sensitivity=true`
   CLI example.

## Decisions log (linked to grill-me Q&A)

| # | Decision |
|---|---|
| Q1 | Patterns-first; pattern → template-instance mapping must be visible. |
| Q2 | §4.14 layers two patterns: extraction-as-its-own-class (structural) + iterate-the-namespace (refinement). |
| Q3a | §2 Runner stage list = flat. Dispatch named separately. |
| Q3b | §2 layer table = 4 rows, prose trimmed of repo-specific filenames. |
| Q4 | §5.1 reframes sensitivity dispatch as a Hydra config-design pattern (enum-in-group, not sibling boolean). |
| Q5 | §2 bullet → two-mode rule (`cfg` for config inputs, `data` for computed quantities). |
| Q6 | README: keep HEAD, drop master side; fix CLI flag. |
| Q7 | §8 `Code/` bullet dropped (repo-specific). |
| Q8 | §8 rewritten as portable anti-patterns; non-portable items dropped. |
