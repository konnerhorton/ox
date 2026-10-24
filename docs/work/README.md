# Units of work

One file per unit of work (a feature, fix or decision), named after its branch: `<branch>.md`.

Each file grows one section per step, each in its own commit:

1. `## Intent`: goal, why, constraints, out of scope.
2. `## Spec`: decisions and numbered acceptance criteria (only when the feature has no other spec home).
3. `## Plan`: the build commits in order, the files each touches, and the tests that prove each criterion.

Once a unit is merged, its file is history: `SPEC.md`, the code, tests and user docs are the source of truth.
These files are excluded from the docs site (`exclude_docs` in `mkdocs.yml`).

`TODO.md` here is the backlog: items not yet decided or researched, referenced as "TODO #n".
