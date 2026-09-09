# MkDocs And GitHub Pages Step By Step

## Current Publishing Path

The repository uses `mkdocs.yml`, pinned `requirements-docs.txt`, and a single
Pages publishing workflow, `.github/workflows/publish-docs.yml`. There is no
active `static.yml` workflow to configure. The workflow builds the documentation,
generates the governance graph/viewer, copies `generated/` into `site/generated/`,
and deploys the Pages artifact through the `github-pages` environment.

## 1. Edit On A Branch

Follow the [beginner change guide](beginner-step-by-step-operations-guide.md).
Edit the source Markdown and update `mkdocs.yml` when adding a navigable page.
Use relative Markdown links to other documentation pages. Historical release
notes and reference runs describe their recorded revision; link current
procedures instead of rewriting frozen baseline material.

## 2. Build Locally

From the repository root:

```bash
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
python3 -m venv .venv-docs
.venv-docs/bin/python -m pip install -r requirements-docs.txt
.venv-validation/bin/python scripts/generate_governance_graph.py
.venv-validation/bin/python scripts/generate_status_viewer.py
.venv-docs/bin/mkdocs build --strict
mkdir -p site/generated
cp -R generated/. site/generated/
```

The final copy matches the publishing workflow and makes generated report/viewer
links available. Preview the built site:

```bash
.venv-docs/bin/python -m http.server 8000 --directory site
```

Open `http://localhost:8000/`. Inspect the changed pages, navigation and viewer
links. Stop the server with Ctrl-C. Build success checks rendering/configuration;
it does not establish that every statement agrees with implementation.

Inspect generated differences before committing. Exclude timestamp-only noise
and local `site/`/virtual environments. Do not edit historical evidence or released
packages to resolve a documentation build issue.

## 3. Review And Merge

Commit the intended source files, push the feature branch and open a PR. Main
requires the configured checks and one authorized approving review. The Pages
workflow publishes after merge; it is not a PR preview service. Review the strict
build locally and in Governance CI before merging.

For this public repository, relevant pushes to `main` automatically trigger
publication. The path filter includes documentation, MkDocs/dependencies,
viewer/graph scripts and artifacts, status data, and the publishing workflow.
A change outside those paths alone does not trigger it.

## 4. Verify Publication

Open [Publish Docs](https://github.com/joku-dev/devsecops-governance-framework/actions/workflows/publish-docs.yml),
select the run for the merged commit and check the deployment URL from the
`github-pages` environment. Verify the actual changed page and generated viewer,
not only the job conclusion.

If a rebuild of already accepted main content is needed:

```bash
gh workflow run publish-docs.yml --repo joku-dev/devsecops-governance-framework --ref main
```

The workflow uses GitHub Actions as the Pages source. A repository owner can
inspect **Settings → Pages** and the `github-pages` environment if deployment is
unavailable. Workflow permissions are contents read, Pages write and OIDC token
write. No separate Pages PAT is used.

If the repository becomes private, the workflow skips publication by default.
Its explicit manual `publish_private_pages` input is an intentional publishing
choice; assess visibility and repository support before enabling it.

## Troubleshooting

| Symptom | Check |
|---|---|
| Strict build fails | Missing page/link, YAML indentation, dependency installation and the first build error |
| No automatic run | Merged branch and workflow path filter; changes may not have touched a publishing path |
| Job skipped | Repository visibility and manual private-publishing input |
| Deployment denied | Pages source, workflow permissions, environment protection and run logs |
| Old content remains | Deployment commit and URL; then browser cache |
| Generated link missing locally | Run graph/viewer generation and copy `generated/` into the built site as above |

Return to the [operations handbook](governance-repository-operations-handbook.md)
for accepted evidence, daily monitoring and incident ownership.
