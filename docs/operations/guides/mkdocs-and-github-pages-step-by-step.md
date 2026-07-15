# MkDocs And GitHub Pages Step By Step

## Purpose

This guide explains exactly how documentation publishing works in this repository and how a beginner can use, validate, and publish it safely.

It covers:

- what `MkDocs` does in this repository
- how to build the documentation locally
- how to preview the documentation locally
- how GitHub Pages publishing works
- how to change documentation navigation safely
- how to troubleshoot common problems

## What MkDocs Does Here

`MkDocs` turns the Markdown files in `docs/` into a static documentation website.

In this repository:

- the Markdown source lives in `docs/`
- the site navigation is controlled by `mkdocs.yml`
- the generated website is written into `site/`
- GitHub Actions can publish that generated site to GitHub Pages

## What Files Matter

The most important files are:

- `docs/` for the actual documentation pages
- `docs/index.md` for the documentation landing page
- `mkdocs.yml` for the website navigation structure
- `requirements-docs.txt` for the Python package needed to build the docs
- `.github/workflows/publish-docs.yml` for repository-managed documentation publishing
- `.github/workflows/static.yml` for the GitHub-generated Pages deployment workflow

## Step 1: Understand The Publishing Model

This repository currently uses the following model:

1. write or update Markdown files under `docs/`
2. keep the page navigation aligned in `mkdocs.yml`
3. run `mkdocs build --strict` locally to validate the site
4. push the changes
5. GitHub Actions publishes the static site to GitHub Pages

## Step 2: Create A Local Python Environment

From the repository root:

```bash
python3 -m venv .venv-docs
. .venv-docs/bin/activate
pip install -r requirements-docs.txt
```

What this does:

- creates an isolated Python environment in `.venv-docs`
- activates that environment for the current shell
- installs `MkDocs`

## Step 3: Build The Site Locally

Run:

```bash
mkdocs build --strict
```

What this does:

- reads `mkdocs.yml`
- reads the pages under `docs/`
- builds the static site into `site/`
- fails if the navigation is wrong or referenced files are missing

Why `--strict` matters:

- it prevents publishing a broken documentation structure
- it catches missing files and navigation mistakes early

## Step 4: Preview The Site Locally

Run:

```bash
mkdocs serve
```

Then open the local address printed by MkDocs, typically:

```text
http://127.0.0.1:8000/
```

What this does:

- starts a local preview server
- lets you click through the site as if it were already published
- automatically refreshes when you edit documentation files

## Step 5: Add A New Documentation Page

Example:

1. create a new file:

```bash
touch docs/operations/example-doc-page.md
```

2. add content:

```markdown
# Example Doc Page

This is an example documentation page.
```

3. add the page to `mkdocs.yml`

Example nav entry:

```yaml
- Operations:
    - Example Doc Page: operations/example-doc-page.md
```

4. validate:

```bash
mkdocs build --strict
```

If the build succeeds, the page is correctly wired into the documentation site.

## Step 6: Change The Navigation Safely

Navigation is defined in `mkdocs.yml`.

Example:

```yaml
- Releases:
    - Overview: releases/index.md
    - L1 Baseline v1.0.0: releases/l1-baseline-v1.0.0.md
```

Rules to follow:

- every referenced page must exist under `docs/`
- use repository-relative paths inside the `docs/` tree
- after every nav change, run:

```bash
mkdocs build --strict
```

## Step 7: Understand The GitHub Workflows

There are two relevant workflows:

### Repository-managed workflow

File:

- `.github/workflows/publish-docs.yml`

This workflow:

1. checks out the repository
2. installs `MkDocs`
3. runs `mkdocs build --strict`
4. uploads the built `site/`
5. deploys the site to GitHub Pages

### GitHub-generated Pages workflow

File:

- `.github/workflows/static.yml`

This file can appear when GitHub Pages is initialized through the GitHub UI using `Static HTML`.

Operational meaning:

- GitHub may create a default deployment workflow
- the repository may therefore contain both:
  - the repository-managed `publish-docs.yml`
  - the GitHub-generated `static.yml`

## Step 8: Decide Which Workflow Is The Official One

Recommended operational rule:

- keep exactly one publishing model as the official one
- document it clearly
- avoid having multiple active documentation deployment workflows unless that is intentional

In this repository, the intended managed publishing workflow is:

- `.github/workflows/publish-docs.yml`

If `static.yml` is still present, treat it as GitHub-generated Pages scaffolding and review whether it should remain active long-term.

## Step 9: Publish Documentation Through GitHub

After pushing documentation changes to `main`:

1. GitHub Actions runs the documentation publishing workflow
2. the site is built again in CI
3. GitHub Pages publishes the static output

You can inspect the runs in:

- the repository `Actions` tab

You can inspect the Pages configuration in:

- `Settings -> Pages`

Expected configuration:

- source or deployment model based on `GitHub Actions`

## Step 10: Verify That Publishing Works

Check these things:

1. local build passes:

```bash
mkdocs build --strict
```

2. the GitHub Actions docs workflow succeeds
3. the published Pages site is reachable

## Step 11: Troubleshoot Common Problems

### Problem: page exists but is not visible in the site

Cause:

- the file exists in `docs/`
- but it is not referenced in `mkdocs.yml`

Fix:

- add the page to the `nav` section in `mkdocs.yml`

### Problem: `mkdocs build --strict` fails

Common causes:

- wrong file path in `mkdocs.yml`
- page moved but nav not updated
- broken Markdown link assumptions

Fix:

- read the failing path
- verify the file exists
- correct the path in `mkdocs.yml`

### Problem: GitHub Pages workflow fails

Common causes:

- Pages not yet initialized in repository settings
- workflow permissions not sufficient
- multiple deployment workflows create confusion

Fix:

1. open `Settings -> Pages`
2. verify GitHub Actions deployment is enabled
3. inspect the failing workflow run in `Actions`

### Problem: local Python install fails

Cause:

- system Python may be externally managed

Fix:

- use a virtual environment:

```bash
python3 -m venv .venv-docs
. .venv-docs/bin/activate
pip install -r requirements-docs.txt
```

## Step 12: Recommended Daily Working Pattern

Use this sequence every time:

1. edit or add documentation in `docs/`
2. update `mkdocs.yml` if navigation changed
3. run:

```bash
mkdocs build --strict
```

4. optionally preview:

```bash
mkdocs serve
```

5. commit and push
6. verify the GitHub Actions publishing run

## Example End-To-End Session

Example commands:

```bash
cd /workspace/devsecops-governance-as-code
python3 -m venv .venv-docs
. .venv-docs/bin/activate
pip install -r requirements-docs.txt
touch docs/operations/example-doc-page.md
mkdocs build --strict
mkdocs serve
```

Then:

- update `mkdocs.yml`
- rebuild
- commit
- push
- verify the Pages deployment in GitHub Actions

## Operational Recommendation

If this repository is used as an enterprise governance source, the documentation publishing workflow should be treated like any other governed process:

- changes should be reviewed
- the publishing workflow should be stable
- the navigation should remain intentional
- release-relevant documentation should be versioned and linked from the release section
