# `.specify/` — spec-kit infrastructure

Convention files for the [spec-kit](https://github.com/github/spec-kit) workflow. The actual specs live in [`../specs/`](../specs/) — one folder per feature, each with `spec.md`, `plan.md`, `tasks.md`, plus optional `data-model.md`, `contracts/`, `quickstart.md`, `research.md`.

## Layout

```
.specify/
├── README.md             this file
├── memory/
│   └── constitution.md   non-negotiable project principles
└── templates/
    └── (spec/plan/tasks templates — add as needed)
```

## How to author a new spec

1. Pick the next spec number (look at `specs/` for the highest existing).
2. Create `specs/NNN-feature-slug/spec.md` from the format used in spec 006.
3. Iterate via the speckit phases: `/specify` → `/clarify` → `/plan` → `/tasks` → implement.
4. Each plan must address every principle in [`memory/constitution.md`](memory/constitution.md) (PASS / N/A justified / FAIL).
5. Mark the spec `Status: Complete` and link to the verifying PR/release once shipped.
