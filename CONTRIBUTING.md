# Contributing & Git Conventions

These rules define how commits, branches, and PRs are made in this repository.
**They are mandatory** — including for any AI-assisted session. Read before committing.

## 1. Commit identity (non-negotiable)

Every commit MUST be authored *and* committed as **Shaunak1012** only:

```
Name : Shaunak1012
Email: 195268122+Shaunak1012@users.noreply.github.com
```

Set it locally (already configured in this repo, but verify after re-clone):

```bash
git config --local user.name  "Shaunak1012"
git config --local user.email "195268122+Shaunak1012@users.noreply.github.com"
```

**Never** add co-author or assistant attribution of any kind — no
`Co-Authored-By:` trailers, and nothing mentioning "Claude", "Anthropic", or
"Generated with …" in commit messages or PR bodies. All work is attributed
solely to Shaunak1012.

## 2. Commit messages — Conventional Commits

Format: `type(scope): short imperative description`

- **Types:** `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `build`, `ci`
- **scope** (optional): the area touched — e.g. `pipeline`, `cnn`, `behaviour`, `ltn`, `kg`, `fusion`, `docs`
- One **logical change per commit**, with a clear description of *what* is committed.
- **Never** force the whole project into a single "add everything" commit.

Examples:
```
feat(ltn): add behaviour-grounded LTN reasoning
docs: record full-run LTN results in STATUS
fix(behaviour): correct ScanProbe duration threshold
chore: add .gitattributes for line-ending normalisation
```

## 3. Branching & PR workflow (GitHub Flow)

- Do **not** commit feature work directly to `main`.
- **Branch names:** `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `chore/<topic>`.
- Flow per unit of work:
  ```bash
  git checkout main
  git checkout -b feat/<topic>
  git add <specific files>
  git commit -m "feat(scope): ..."
  git push -u origin feat/<topic>
  gh pr create --base main --head feat/<topic> --title "..." --body "..."
  git checkout main
  gh pr merge feat/<topic> --merge --delete-branch
  git fetch origin && git reset --hard origin/main
  ```
- Use **merge commits** (`--merge`) to keep the branch topology visible.
- Stage work into **logical, self-contained PRs** — never one big dump.

## 4. What not to commit

Gitignored (regenerable / large / machine-specific):
`.venv/`, `data/`, `models/`, `outputs/{arrays,embeddings,predictions,metadata}/`, `outputs/*.log`.

Only **finalised** result figures under `outputs/figures/*.png` are tracked —
do **not** commit smoke-test or placeholder plots.

## 5. Dataset note

The MIT license covers **code only**. CIC-IDS2017 has its own usage terms —
cite Sharafaldin et al. (2018) and the Canadian Institute for Cybersecurity.
