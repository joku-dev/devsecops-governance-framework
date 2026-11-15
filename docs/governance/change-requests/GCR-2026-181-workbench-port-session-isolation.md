# GCR-2026-181 — Workbench sessions across localhost ports

Date: 2026-11-15. Classification under the [artifact intake process](../../operations/processes/new-artifact-intake-process.md): focused application correction for portability AC26, not a normative source or authority assignment.

Browser cookies are scoped to hosts/paths, not TCP ports. With a Mac Workbench and an SSH-forwarded VM Workbench on different localhost ports, the old shared `axiom_session` cookie name let the second login overwrite the first instance's cookie. Separate server memory/keys alone did not prevent that browser conflict.

Each Workbench now names its session cookie using its actual bound port. Login, lookup and logout use that same instance-specific name. HttpOnly, SameSite=Strict, CSRF checks, host/origin restrictions, private keys/drafts and publisher settings retain their behavior. Existing unscoped cookies are ignored; users sign in again after updating. This does not update either running host or grant another publication owner.

A regression runs two actual HTTP servers through one standard browser-style cookie jar: both stay authenticated and logout from one leaves the other authenticated. The earlier separate-client test remains for key/session/draft isolation. Existing accepted governance files and baselines remain unchanged.
