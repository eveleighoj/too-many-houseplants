# Contributing: commits, branches and CI

## Commit messages: Conventional Commits

Every commit must be a [Conventional Commit](https://www.conventionalcommits.org):

```
<type>[(scope)][!]: <description>

feat(trips): add stays to the trip view
fix: return 404 for an unknown spot
docs: explain the seed ids
feat!: rename owner_id to user_id          ← ! marks a breaking change
```

| Type | For |
| --- | --- |
| `feat` | a new feature |
| `fix` | a bug fix |
| `docs` | documentation only |
| `test` | tests only |
| `refactor` | code changes that neither fix a bug nor add a feature |
| `perf` | performance |
| `build` | dependencies, Docker, packaging |
| `ci` | the CI workflow |
| `chore` | anything else, e.g. tooling config |
| `style` | formatting only |
| `revert` | reverting an earlier commit |

Scopes are optional and free-form. Use the area you changed: `trips`, `windsurf`,
`trips-frontend`, `auth`, `seed` and so on.

A PR can hold several commits, e.g. two features and a fix. Each one lands on `main`
unchanged, so make each commit a meaningful, conventional step.

### How it's enforced

- **Locally:** a `commit-msg` hook rejects a badly formatted message before the commit is
  made. `make setup` installs it (`.pre-commit-config.yaml`). It allows `fixup!` commits and
  merge commits, so it doesn't get in your way mid-rebase.
- **In CI:** every commit a PR adds is checked strictly. Merge commits and leftover
  `fixup!` / `squash!` commits fail. Run the same check locally with `make check-commits`.

## Branches and merging: rebase, never merge

PRs are **rebased and merged**: each commit is replayed onto `main`, with no merge commit,
so `main`'s history stays linear.

```bash
git switch -c feat/trip-editing        # branch off main
# ...commit as you go, conventionally...

git fetch origin
git rebase origin/main                 # update your branch: never `git merge main`
git push --force-with-lease            # after rebasing (refuses if someone else pushed)
```

Tidy up before opening or merging a PR. Squash "oops" commits into the commits they fix,
and reword any unclear messages:

```bash
git commit --fixup <sha>               # a fix for an earlier commit on this branch
git rebase -i --autosquash origin/main # folds fixups in; mark commits `reword` to rename them
```

**Stacked PRs** (a branch built on another unmerged branch) work. When the lower PR merges,
`git rebase origin/main` on the upper branch usually drops the already-merged commits
automatically. If it doesn't, use `git rebase --onto origin/main <old-base-branch>`.

## CI: the Test workflow

The **Test** workflow (`.github/workflows/test.yml`) runs on every PR and on pushes to `main`. Jobs only run when their
part of the repo changed (a skipped job counts as passing):

| Job | Checks | Locally |
| --- | --- | --- |
| `commits` | every commit in the PR is a Conventional Commit, with no merge commits | `make check-commits` |
| `secrets` | gitleaks over the whole history (`.gitleaks.toml`) | — |
| `layout` | every folder under `tests/` has an `__init__.py` | `make check-test-packages` |
| `api` | ruff, import-linter boundaries, every api test (testcontainers runs Postgres), then the Docker `test` and `runtime` stages | `make lint`, `make test-api`, `make build` |
| `frontends` | prettier, eslint, svelte-check, unit and component tests, production builds, Docker images | `make lint`, `make test-frontends`, `make build` |
| `api-types` | the frontends' generated API types match the api | `make api-types-check` (fix with `make api-types`) |
| `Test result` | every job above passed or was skipped on purpose; **the one check `main` requires** | — |

## One-time GitHub settings

Repo owners only. Under **Settings**:

- **General → Pull Requests:** tick only **Allow rebase merging**. Untick merge commits and
  squash merging, so every PR merges the same way. Optionally tick **Always suggest updating
  pull request branches**.
- **Rules → Rulesets → New branch ruleset** targeting `main`:
  - **Require linear history** (blocks merge commits on `main`)
  - **Require a pull request before merging**
  - **Require status checks to pass**, adding just one check: **`Test result`**. It's a
    final job that passes only if every other job passed or was deliberately skipped, so new
    jobs never need adding here. Enable **Require branches to be up to date before merging**
    so each PR is tested against the latest `main`.
  - **Block force pushes**, for `main` only. Force-pushing your own branches after a rebase
    is expected.
