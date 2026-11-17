# format-vocabulary: a small vocabulary for the session `format:` field

## Intent

### Goal
A session's `format:` value can be written in a small, documented vocabulary (a quoted protocol name
plus fixed arguments), and a builtin plugin parses it into structured timing: interval, work, rest
and movement groups. Values outside the vocabulary still load, and the plugin lists them.

### Why
- `format:` is free text today (`STATUS.md` Open), so it can't be queried beyond string
  matching. `docs/drafts/future.md` "Protocol metadata" asks for standard names for EMOM, alt-EMOM,
  ladders, etc. so a session's layout can still be understood years later.
- Evidence from a real log (~1150 sessions): 257 `format:` lines had already settled into a few
  shapes: `"emom"` (198), `"alt-emom" PT30M` (20), `"emom" PT30M` (16), `"fighter-ladder"` (11),
  `"e2mom"` (8), `"circuit"` (2). Supersets ("first two done as superset, next 3 done as superset,
  then last 2"), work/rest running intervals (1 min hard / 1 min jog, a planned Norwegian 4x4) and
  pavel sprints were only recorded in notes and movement names.
- Work/rest ratios were considered as a per-set `rest` keyword and rejected (see Decisions 1–2).
  `format:` already exists, is session-level, and covers the need without new set syntax.
- Trying it as a plugin first lets the vocabulary settle in real use before anything moves into the
  grammar.

### Constraints
- **No grammar change.** `format:` stays `text_until_newline` (`tree-sitter-ox/grammar.js`). The
  vocabulary lives in the plugin until it has settled; moving it into the grammar is a later unit.
- SPEC Non-Goals: "the `.ox` format stays simple enough to read with no tooling." A format value
  should read as plain English to someone who has never seen ox.
- SPEC "Plain text is the source of truth": a value the plugin can't parse is never rewritten or
  dropped. It is reported, not rejected.
- `format:` describes timing structure only. Round counts come from the sets (`4x1`, `3x6`) and total
  duration from `srpe:`, so the format never repeats them and can't contradict them.
- The parse function is plain Python, separate from the plugin's output code, so the same rules can
  be ported to the grammar later.

### Vocabulary (first version)

The whole value is one quoted string: `format: "<name> [args]"`.

| Value | Meaning |
|---|---|
| `"emom [interval]"` | One set starts every `interval` (default `PT1M`); sub-minute intervals allowed, e.g. `"emom PT30S"`. `"emom PT2M"` replaces `e2mom`. |
| `"alt-emom [interval]"` | Like `emom`, but rotating through the movements, one per interval. |
| `"intervals <work>:<rest>"` | Fixed work and rest durations, e.g. `"intervals PT1M:PT1M"`, `"intervals PT4M:PT3M"` (Norwegian 4x4). |
| `"superset <n>-<n>-…"` | Movements grouped in listed order, e.g. `"superset 2-3-2"` for 7 movements. |
| `"pavel-sprints"` | Named protocol, no arguments: one set = 6 sprints of 8s work / 22s rest, then 2 min walking rest. Logged as `pavel-sprints: 3x6`. |
| `"ladder"` | Named protocol, no arguments (replaces `fighter-ladder`). |
| `"circuit"` | Named protocol, no arguments. |

No `format:` means straight sets (e.g. 5/3/1 sessions).

Examples from the converted log:

```
@session
date: 2026-10-21
name: run-intervals
format: "intervals PT1M:PT1M"
run-warmup: PT10M
run-interval: 3x1 PT1M "80% effort"
run-recovery: 3x1 PT1M "easy jog"
srpe: 3 PT16M
@end

@session
date: 2026-09-02
name: conditioning
format: "pavel-sprints"
pavel-sprints: 3x6 50yd
srpe: 3 PT13M
@end
```

### Out of scope
- Grammar, LSP and `ox lint` support for format values (a later unit, once the vocabulary settles).
- `tabata`, `amrap`, `rft`, `complex` and other names not yet used in a real log. They get added
  when they are first logged.
- Formats for part of a session (e.g. a finisher block after straight sets). Not needed today;
  5/3/1 sessions are all straight sets.
- Mapping a format name to a fuller definition written once elsewhere (`@template`, named-session
  definitions): TODO #6. Until then, a named protocol's meaning lives in the plugin's vocabulary table.
- Per-set rest fields and intensity fields (%, HR zones).
- Migrating old logs. `scripts/migrate_ox.py` stays as is; the one real log has been converted by hand.

### SPEC sections touched
- None. Status moved out of SPEC at checkpoint 1: `STATUS.md` Done (new builtin) and Open (`format:` is
  no longer only free text).
- Docs: `docs/getting-started.md` (session field table, which still shows the `5/3/1 wave` example),
  `docs/plugins.md` (new plugin section), `docs/drafts/future.md` "Protocol metadata" (point to this
  vocabulary), `CHANGELOG.md`.

### Decisions (intent review, 2026-10-24)
1. **Timing goes in session-level `format:`, not in new per-set keywords** (`rest PT1M`,
   `every PT1M`). Rest usually belongs to a round of several movements, not to one movement. It is
   mostly planned rather than measured. And keywords would bring `key value` syntax into lines that
   are currently plain values.
2. **A name plus fixed arguments (option B).** Rejected: names only (every variation needs a new
   name) and combinable keywords like `on PT4M off PT3M` (keyword creep, harder to read at a
   glance). Internally the plugin can reduce each name to interval/work/rest values, which are what
   a grammar would need later.
3. **One `emom` with an optional interval, no `eNmom` names.** `"emom PT2M"` replaces `e2mom`, and
   `"emom PT30S"` covers sub-minute timing.
4. **No time-cap argument.** Session duration comes from `srpe:`. The old `"emom" PT30M` meant a
   30-minute cap; under this vocabulary it would mean a 30-minute interval, so the cap was dropped.
   In the real log, the 18 affected sessions without `srpe:` got `note: "30 min session"` to keep
   the duration.
5. **Superset groups use `-` (`"superset 2-3-2"`), not `/`.** This keeps them distinct from the
   per-set `/` lists in the movement syntax. Can change later.
6. **The whole value is quoted** (`"emom PT2M"`, not `"emom" PT2M` or `emom PT2M`). This keeps the
   line free of syntax errors in the editor, and makes it unambiguous where the value starts and
   ends. The plugin strips the quotes before parsing.
7. **`fighter-ladder` becomes `ladder`.**
8. **`intervals` has no set-rest argument.** A third argument for rest between sets (for pavel
   sprints) was rejected as verbose and confusing. Multi-level protocols get a name instead
   (`"pavel-sprints"`), and a fuller way to define them is TODO #6.
9. **`intervals` takes one `<work>:<rest>` argument** (`"intervals PT1M:PT1M"`), amended
   2026-11-17. It reads the way coaches write ratios ("1:1", "4:3"), work first. Rejected: labeled
   `work-PT1M rest-PT1M` (verbose), labeled `work:PT1M` (looks like a nested `key: value` field), and
   `PT1M/PT1M` (clashes with per-set `/` lists, as in Decision 5). A colon is safe here: ISO 8601
   durations never contain one, the grammar reads `format:` as text to the end of the line, and both
   highlighters anchor their field rules at the start of the line.
10. **Pavel sprints are counted as sets of 6 sprints** (`3x6`, not `3x1`), matching the 2025 entries.
    The 2026 entries that used `Nx1` for N rounds were converted.

### Open for the spec step
Resolved in `## Spec`, Decisions.
