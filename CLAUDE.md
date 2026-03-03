# CLAUDE.md

This file provides guidance to AI assistants (Claude, etc.) working in this repository.

## Repository Status

This is a freshly initialized repository with no source code yet. This CLAUDE.md establishes conventions and workflows to follow as the project grows.

## Project Overview

- **Repository**: SzymonZimnyprog/SzymonZimnyprog
- **Status**: Initialized, awaiting project files
- **Branch strategy**: Feature branches prefixed with `claude/` for AI-assisted sessions

## Git Conventions

### Branch Naming

- `main` / `master` — stable production branch
- `feature/<short-description>` — new features
- `fix/<short-description>` — bug fixes
- `claude/<session-id>` — AI-assisted session branches (auto-generated)

### Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <short summary>

[optional body]
[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`

Examples:
```
feat(auth): add JWT token validation
fix(api): handle null response from external service
docs: update CLAUDE.md with project conventions
```

### Git Workflow

1. Always develop on a feature branch, never directly on `main`.
2. Push with tracking: `git push -u origin <branch-name>`
3. Keep commits atomic and focused on a single concern.
4. Do not force-push to shared branches without explicit permission.

## Development Workflows

### Before Starting Work

```bash
git fetch origin
git checkout -b feature/<name> origin/main
```

### Running the Project

> Update this section once the project stack is chosen.

```bash
# Placeholder — add actual commands here
# e.g., npm install && npm run dev
# e.g., pip install -r requirements.txt && python main.py
```

### Testing

> Update this section once a test framework is set up.

```bash
# Placeholder — add actual commands here
# e.g., npm test
# e.g., pytest
```

### Linting / Formatting

> Update this section once tooling is configured.

```bash
# Placeholder — add actual commands here
# e.g., npm run lint
# e.g., ruff check . && black .
```

## AI Assistant Guidelines

### What to Do

- Read existing files before editing them.
- Keep changes minimal and focused — only modify what is necessary.
- Prefer editing existing files over creating new ones.
- Write clear, descriptive commit messages explaining *why*, not just *what*.
- Always push to the branch specified in the task context (starts with `claude/`).
- Ask for clarification when requirements are ambiguous before writing code.

### What to Avoid

- Do not push to `main` or `master` without explicit user permission.
- Do not delete files or branches without confirming with the user.
- Do not add unnecessary dependencies, abstractions, or boilerplate.
- Do not introduce security vulnerabilities (SQL injection, XSS, command injection, etc.).
- Do not over-engineer: build the simplest thing that satisfies the requirement.
- Do not add comments, docstrings, or type annotations to code you didn't change.

### Security

- Never commit secrets, API keys, tokens, or credentials.
- Use `.env` files for local secrets and ensure `.gitignore` covers them.
- Validate all external input at system boundaries.
- Prefer well-maintained libraries over custom implementations for auth/crypto.

## File Structure (Template)

Once a technology stack is chosen, update this section with the actual layout:

```
/
├── CLAUDE.md           # This file — AI assistant guidance
├── README.md           # Human-facing project documentation
├── .gitignore
├── src/                # Application source code
├── tests/              # Test files
├── docs/               # Additional documentation
└── <config files>      # e.g., package.json, pyproject.toml, go.mod
```

## Updating This File

Whenever significant project decisions are made (new framework, new conventions, new tooling), update this file to reflect the current state. Keep it accurate and concise — it is the primary reference for AI assistants working in this codebase.
