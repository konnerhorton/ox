# Session Data Model Redesign

Plan document capturing design decisions from the session data model discussion.
Reference this when implementing.

## Design Goals

1. **Unify multi-line entries** into one `@session` structure (named, ad hoc, planned).
2. **Eliminate the ad hoc session gap** — currently, logging many arbitrary movements in a time block requires either a named `@session` (wrong semantics) or many single-line entries (cumbersome).
3. **Make sRPE first-class** — currently hacked in as a fake `Movement` named "srpe" with the value crammed into `.note`, then regex-scraped back out by the plugin.
4. **Generalize set scheme** — support isometric holds and duration-based sets alongside rep-based sets.
5. **Consistent entry markers** — `T`/`W`/`note`/`query` all follow the same `date <marker> ...` shape.

## Syntax Changes

### Single-line entry

Before:
```
2025-01-10 * pullups: BW 5x10
2025-01-10 ! squat: 185lb 3x5
```

After:
```
2025-01-10 T pullups: BW 5x10
```

- `*` replaced by fixed literal `T` (Training) — purely a type marker, not a state flag.
- `!` (planned) removed from single-line entries entirely. Planning is expressed only via `@session` with `completed: false`.
- `T` parallels `W` (weigh-in) as a single capital letter for frequently-typed entry types, while `note`/`query` stay as words for rarely-typed entries.

### Multi-line session block

Before:
```
@session
2025-01-06 * Lower Strength
srpe: "5; PT45M"
squat: 155lb 4x5
deadlift: 185lb 3x5
note: "felt strong"
@end
```

After:
```
@session
date: 2025-01-06
name: Lower Strength
completed: true
srpe: 5 PT45M "felt strong"
squat: 155lb 4x5
deadlift: 185lb 3x5
note: "session went well"
@end
```

Fields:
- `date:` — **required, must be first line** after `@session`
- `name:` — optional. Omit for ad hoc sessions (replaces the need for a separate `@block` construct)
- `completed:` — optional, **default `true`**. Replaces the `*`/`!` flag. Use `completed: false` for planned sessions
- `format:` — optional. Stub field for future `@template` linkage (tracks which structural format/template a session follows, distinct from display `name`)
- `srpe:` — optional, first-class. Accepts: `<integer> <duration> [optional "note"]`
- Movement lines (`item: details`) and `note:` lines follow metadata, in any order
- `@end` closes the block

### Ad hoc session (unnamed)

```
@session
date: 2025-01-10
pullups: BW 3x10
pushups: BW 3x15
jump-rope: PT10M
@end
```

No `name:`, no `completed:` (defaults true). This is the use case that motivated the redesign — grouping arbitrary movements under one date without forcing a session name or repeating `date T` on every line.

### Planned session

```
@session
date: 2025-01-15
name: Upper Day
completed: false
bench-press: 185lb 5x5
pullup: BW 5x8
@end
```

### Set scheme (generalized rep_scheme)

Before — integer reps only:
```
squat: 185lb 3x5
squat: 185lb 5/5/3
```

After — reps OR durations:
```
squat: 185lb 3x5              # 3 sets of 5 reps (unchanged)
squat: 185lb 5/5/3            # varying reps per set (unchanged)
plank: BW 3xPT30S             # 3 sets of 30-second holds (new)
plank: BW PT30S/PT25S/PT20S   # varying hold durations per set (new)
weighted-plank: 45lb 3xPT30S  # weight + duration (new)
```

A set is either rep-based or duration-based. Duration replaces reps for isometric/hold exercises — no need for meaningless `3x1` alongside durations.

### Unchanged syntax

These are not affected:
```
2025-01-10 W 185lb T06:30 "home"        # weigh-in
2025-01-10 note "deload week"            # standalone note
2025-01-10 query "recent" "SELECT ..."   # stored query
@movement squat ... @end                 # movement definition
@template "my-template" ... @end         # template block
@include "other.ox"                      # include directive
@plugin "my_plugin.py"                   # plugin directive
```

## Grammar Changes (`tree-sitter-ox/grammar.js`)

### Remove / modify

- **`flag` rule**: delete `choice("*", "!")`. Single-line entry uses literal `"T"` directly; session blocks use `completed_line` instead.
- **`singleline_entry`**: replace `field("flag", $.flag)` with literal `"T"`.
- **`session_block`**: remove the positional header line (`date flag name`). Replace with `date_line` (required, first) followed by `repeat(choice(...))` of metadata lines, item lines, and note lines.
- **`rep_scheme`**: generalize from `(\d+x\d+)|(\d+(\/\d+)+)` to also accept duration-based forms. The single regex won't stretch — needs to become a proper rule or expanded regex covering `NxPT...` and `PT.../PT...` patterns.

### Add

- **`date_line`**: `seq("date:", field("value", $.date), "\n")` — required first line in session block.
- **`name_line`**: `seq("name:", field("value", $.text_until_newline), "\n")`
- **`completed_line`**: `seq("completed:", field("value", choice("true", "false")), "\n")`
- **`format_line`**: `seq("format:", field("value", $.text_until_newline), "\n")`
- **`srpe_line`**: `seq("srpe:", field("rating", $.integer), field("duration", $.duration), optional(field("note", $.quoted_string)), "\n")`
- **`integer`**: `/\d+/` — bare integer token (nothing in current grammar tokenizes a plain number without a unit suffix, `x`/`/`, or `PT` prefix).

### Disambiguation

- `srpe_line`, `name_line`, `completed_line`, `format_line`, `date_line` use literal keyword prefixes (`"srpe:"`, `"name:"`, etc.) — same pattern as existing `note_line` (`"note:"`) which already takes precedence over generic `item_line`. Tree-sitter resolves via literal match priority.
- `integer` token only appears within `srpe_line` context (gated by `"srpe:"` keyword), so no ambiguity with weight/rep_scheme/duration tokens in generic `details`.
- Duration forms in `rep_scheme` (`3xPT30S`, `PT30S/PT25S/PT20S`) need careful precedence so they don't collide with the standalone `duration` token in `details`. The `/`-separated form and `Nx` prefix distinguish them from a bare `PT30S` duration.

## Data Model Changes (`src/ox/data.py`)

### `Entry` base class

```python
# Before
@dataclass(frozen=True, slots=True)
class Entry:
    date: datetime.date
    flag: str

# After
@dataclass(frozen=True, slots=True)
class Entry:
    date: datetime.date
    completed: bool = True
```

### `TrainingSet`

```python
# Before
@dataclass(frozen=True, slots=True)
class TrainingSet:
    reps: int
    weight: Optional[Quantity] = None

# After
@dataclass(frozen=True, slots=True)
class TrainingSet:
    reps: Optional[int] = None
    weight: Optional[Quantity] = None
    duration: Optional[...] = None  # timedelta, pint Quantity, or ISO string — TBD
    # Invariant: exactly one of reps/duration is set per instance
```

### `TrainingSession`

```python
# Before
@dataclass(frozen=True, slots=True)
class TrainingSession(Entry):
    name: str = field()
    movements: tuple[Movement, ...]
    notes: tuple[Note, ...] = ()

# After
@dataclass(frozen=True, slots=True)
class TrainingSession(Entry):
    movements: tuple[Movement, ...]
    name: Optional[str] = None
    notes: tuple[Note, ...] = ()
    format: Optional[str] = None
    srpe_rating: Optional[int] = None
    srpe_duration: Optional[...] = None  # same type TBD as TrainingSet.duration
    srpe_note: Optional[str] = None
```

### `TrainingLog`

- `completed_sessions` / `planned_sessions` properties: filter on `completed == True` / `completed == False` instead of `flag == "*"` / `flag == "!"`.

### `to_ox()` methods

- `TrainingSession.to_ox()`: rewrite entirely.
  - Single movement + no metadata → single-line format: `date T movement.to_ox()`
  - Otherwise → `@session` block with metadata lines + movement lines + `@end`
- `TrainingSet` / `Movement.to_ox()`: handle duration-based sets (emit `3xPT30S` or `PT30S/PT25S` instead of `3x5` or `5/5/3` when duration is populated).

## Parser Changes (`src/ox/parse.py`)

### `process_singleline_entry`

- No longer reads `flag` field from node. Hardcode `completed=True`.
- Otherwise unchanged (still extracts date, item, details → single Movement → TrainingSession).

### `process_session_block` / `process_session_block_completed`

- Rewrite to scan child nodes by type:
  - `date_line` → extract date (required, first)
  - `name_line` → extract name (optional)
  - `completed_line` → extract bool (optional, default True)
  - `format_line` → extract string (optional)
  - `srpe_line` → extract rating (integer), duration, optional note
  - `item_line` → process as Movement (unchanged logic)
  - `note_line` → process as Note (unchanged logic)
- Build `TrainingSession` with all extracted fields.

### `process_details` / set scheme parsing

- Extend to handle duration-based rep schemes:
  - `3xPT30S` → 3 TrainingSets each with `duration=30s`, `reps=None`
  - `PT30S/PT25S/PT20S` → 3 TrainingSets with varying durations, `reps=None`
  - Existing integer forms unchanged.
- Parse duration strings into whatever internal representation is chosen (timedelta, seconds, ISO string).

## Database Changes (`src/ox/db.py`)

### Schema

```sql
-- sessions table
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 1,  -- was: flag TEXT NOT NULL
    name TEXT,
    format TEXT,                            -- new
    srpe_rating INTEGER,                   -- new
    srpe_duration_seconds REAL,            -- new (or minutes — TBD)
    srpe_note TEXT                          -- new
);

-- sets table
CREATE TABLE sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movement_id INTEGER NOT NULL,
    reps INTEGER,                          -- was: NOT NULL; now nullable for duration sets
    weight_magnitude REAL,
    weight_unit TEXT,
    duration_seconds REAL,                 -- new; nullable for rep-based sets
    FOREIGN KEY (movement_id) REFERENCES movements(id)
);

-- training view: add new columns
CREATE VIEW training AS
SELECT
    s.id AS session_id,
    s.date,
    s.completed,                           -- was: s.flag
    s.name AS session_name,
    s.format AS session_format,            -- new
    s.srpe_rating,                         -- new
    s.srpe_duration_seconds,               -- new
    m.id AS movement_id,
    m.name AS movement_name,
    m.note AS movement_note,
    t.id AS set_id,
    t.reps,
    t.weight_magnitude,
    t.weight_unit,
    t.duration_seconds                     -- new
FROM sessions s
JOIN movements m ON m.session_id = s.id
JOIN sets t ON t.movement_id = m.id;
```

### `create_db`

- Update INSERT statements for sessions (new columns) and sets (new duration column).
- `flag` parameter → `completed` (1/0 integer).

## Plugin Changes (`src/ox/builtins/srpe.py`)

### Before (current hack)

`_extract_srpe_data` runs two SQL queries:
1. Find movements named "srpe", regex-parse their `.note` field for `"rating; duration"`.
2. Find other movements whose `.note` contains `"srpe: ..."`, regex-parse it.

### After

Single query against `sessions` table:
```sql
SELECT date, srpe_rating, srpe_duration_seconds
FROM sessions
WHERE srpe_rating IS NOT NULL
ORDER BY date
```

- Delete `_SRPE_PATTERN` regex.
- Delete both "Case 1" and "Case 2" scanning paths.
- `_parse_iso_duration_minutes` may still be needed if duration is stored as ISO string; unnecessary if stored as seconds/minutes.

## Files Affected

| File | Change scope |
|------|-------------|
| `tree-sitter-ox/grammar.js` | Major rewrite: new rules, modified rules, removed flag |
| `src/ox/data.py` | Entry.flag→completed, TrainingSet.duration, TrainingSession fields |
| `src/ox/parse.py` | Rewrite session block processing, extend set scheme parsing |
| `src/ox/db.py` | Schema changes, updated INSERT logic, updated view |
| `src/ox/builtins/srpe.py` | Simplify to query sessions table directly |
| `src/ox/cli.py` | Update any flag references (check for `"*"`/`"!"` usage) |
| `src/ox/lsp.py` | Update completion/diagnostics if they reference flag or session header |
| `src/ox/lint.py` | Check for flag references |
| `examples/example.ox` | Rewrite all entries to new syntax |
| `examples/advanced.ox` | Rewrite all entries to new syntax |
| `tests/conftest.py` | Rewrite all fixtures to new syntax |
| `tests/test_parse.py` | Update assertions for new data model fields |
| `tests/test_data.py` | Update for flag→completed, new fields |
| `tests/test_db.py` | Update for schema changes |
| `tests/test_reports.py` | Check for flag references |
| `tests/test_plugins.py` | Check for flag references |
| `tests/test_integration.py` | Update for new syntax |
| `tests/test_srpe.py` | Rewrite for first-class srpe fields |
| `CLAUDE.md` | Update .ox format documentation section |

## Open Decisions (to resolve at implementation time)

1. **Duration internal representation**: `timedelta`, `pint.Quantity` (for consistency with weight), raw seconds as float, or ISO string. Affects `TrainingSet.duration`, `TrainingSession.srpe_duration`, and DB column type.
2. **`format` field semantics**: free text for now, or must reference a `@template` name? Likely free text stub until `@template` processing is built.
3. **Ordering within `@session`**: `date:` must be first. Should other metadata lines (`name:`, `completed:`, `srpe:`) be required before movement lines, or can they appear anywhere interspersed with movements? Requiring metadata-before-movements is simpler to parse and read.
4. **Migration tooling**: write a script to convert existing `.ox` files from old syntax to new, or manually rewrite examples/tests?
5. **Backward compatibility period**: support both old and new syntax temporarily, or clean break?
