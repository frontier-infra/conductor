# Security Policy

## Read this before running

The Hermes Multi-Agent Workflow runs **LLM-authored code** (on any "build" path),
**shells out**, and acts **autonomously** between detection and the human gate.
It is a powerful, dual-use automation tool. Understand the trust surface in
[`docs/06-security.md`](docs/06-security.md) before deploying it.

Key points:

- **Untrusted input → model context.** Scouts fetch web content that becomes task
  bodies a model reads. This is a prompt-injection surface. The human gate and the
  per-path **scope rails** (`paths/rails/*.md`) are the controls that sit between
  untrusted input and any privileged action. Keep the rails tight.
- **The human gate is mandatory.** It bounds cost and keeps a person between
  research and fulfillment. Do not modify it to auto-approve.
- **Least privilege.** Give each Hermes profile the minimum toolset for its role.

## Never commit secrets

This repository must never contain `.env` files, OAuth token stores
(`auth.json`), board databases (`*.db`), or generated item/vault data. The
`.gitignore` excludes these. Document required variables in `.env.example` only.

Run the pre-publish checklist in [`docs/06-security.md`](docs/06-security.md)
before pushing or open-sourcing an adapted copy.

## Reporting a vulnerability

If you find a security issue in this template, please open a GitHub issue marked
`security`, or contact the maintainer privately if the issue is sensitive. There
is no warranty (see `LICENSE`); use at your own risk.
