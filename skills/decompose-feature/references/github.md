# GitHub commands

All commands use the `gh` CLI. Replace `OWNER/REPO`, numbers and titles.

## Prerequisites

- GitHub Projects needs the `project` scope: check with `gh auth status`. If it's missing, ask the user to run `! gh auth refresh -s project` (it's interactive).
- Find the repo: `gh repo view` (inside the project folder) or `gh repo list OWNER`.
- Find the Project: `gh project list --owner OWNER`.
- If either is missing, see the next section. Create nothing until the user has confirmed the settings.

## Creating a repo or Project

Propose these settings to the user, with a recommended value for each, and create only after they confirm.

### Repo

| Setting | Recommended default |
|---|---|
| Owner | The user's personal account (ask if an organization is meant) |
| Name | The project folder name, in kebab-case |
| Visibility | Private |
| Description | One line from the plan's goal |
| `.gitignore` | Template for the stack, e.g. `VisualStudio` for .NET, `Node` for JS/TS (skip if the folder already has one) |
| License | None for private repos; MIT if it will be public |
| README | Yes for an empty repo; no if the folder already has one |
| Local folder | Connect it as `origin` if the project already exists locally |

```bash
# New, empty repo on GitHub
gh repo create OWNER/NAME --private --description "<desc>" --gitignore VisualStudio --add-readme

# Repo for an existing local folder (no --push: pushing needs the user's explicit request)
gh repo create OWNER/NAME --private --description "<desc>" --source . --remote origin
```

Use `--public` instead of `--private` and add `--license mit` when agreed.

### Project

| Setting | Recommended default |
|---|---|
| Owner | Same owner as the repo |
| Title | The project or feature name |
| Visibility | Private (same as the repo) |
| Linked repo | The repo above |

```bash
gh project create --owner OWNER --title "<title>"          # prints the project number and URL
gh project edit <project-number> --owner OWNER --visibility PRIVATE
gh project link <project-number> --owner OWNER --repo OWNER/REPO
```

## Labels and colours

Create the labels that don't exist yet (`gh label list -R OWNER/REPO` to check). `--force` updates an existing label's colour.

| Label | Colour | Meaning |
|---|---|---|
| `type:epic` | `3E4B9E` | Epic |
| `type:story` | `0075CA` | Story |
| `type:task` | `BFD4F2` | Task |
| `area:frontend` | `1D76DB` | UI, client code |
| `area:backend` | `0E8A16` | Server, APIs, business logic |
| `area:database` | `5319E7` | Schema, migrations, queries |
| `area:cloud` | `D93F0B` | Infrastructure, CI/CD, hosting |
| `area:assets` | `FBCA04` | Images, icons, sounds, content |
| `area:design` | `E99695` | UX/UI design, mockups |
| `area:testing` | `006B75` | Test suites, test infrastructure |
| `area:docs` | `C5DEF5` | Documentation |

```bash
gh label create "area:backend" --color 0E8A16 --description "Server, APIs, business logic" -R OWNER/REPO --force
```

## Creating issues

```bash
gh issue create -R OWNER/REPO --title "<title>" --body-file <file> --label "type:task,area:backend"
```

Write each body to a temporary file in the scratchpad and pass it with `--body-file`, to avoid quoting problems. `gh issue create` prints the issue URL; the number is at the end.

Add each issue to the Project:

```bash
gh project item-add <project-number> --owner OWNER --url <issue-url>
```

## Linking

The sub-issue and dependency endpoints take the issue's numeric **id**, not its number. Get it with:

```bash
gh api repos/OWNER/REPO/issues/<number> --jq .id
```

Make an issue a sub-issue of a parent:

```bash
gh api -X POST repos/OWNER/REPO/issues/<parent-number>/sub_issues -F sub_issue_id=<child-id>
```

Mark an issue as blocked by another:

```bash
gh api -X POST repos/OWNER/REPO/issues/<blocked-number>/dependencies/blocked_by -F issue_id=<blocking-id>
```

Also keep "Blocked by #N" in the task body, so the dependency is visible even where the UI doesn't show it.

A `422` can mean you are creating content too fast: wait a few seconds and retry that call.
