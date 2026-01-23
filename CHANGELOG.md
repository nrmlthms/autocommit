# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-01-24

### Added
- `--preview` flag to preview changes and generated commit message without committing
- `--amend` flag to amend the last commit instead of creating a new one
- `--scope` parameter to add scope to conventional commit messages (e.g., `feat(auth): ...`)
- Commit history analysis to learn and match user's commit style
- `unstage_all()` method to detector for unstaging all changes
- GitHub Actions CI/CD workflows for testing, linting, type checking, and security scanning
- PyPI publishing workflow for automated releases
- Pre-commit hooks configuration (`.pre-commit-hooks.yaml`)
- Python 3.13 support

### Changed
- Renamed package directory from `autocommit` to `lazycommit` for consistency
- Updated all import paths to use `lazycommit` module name
- Moved development dependencies (twine, mypy) to dev group in pyproject.toml
- Improved CI workflow to explicitly use Python version from matrix

### Fixed
- Fixed all ruff linting issues (45 fixes)
- Fixed all mypy type checking errors (9 fixes)
- Fixed dataclass mutable default arguments
- Fixed duplicate type annotations
- Improved code formatting with ruff format

## [0.1.0] - 2025-01-23

### Added
- Initial release of LazyCommit (formerly AutoCommit)
- AI-powered commit message generation using OpenAI API
- Automatic change detection for staged, unstaged, and untracked files
- CLI commands: `commit`, `config`, `stats`, `undo`
- Interactive commit message review with edit capability
- Safe mode with automatic backup branch creation
- Git state detection (merge, rebase, cherry-pick, etc.)
- Commit message caching to reduce API costs
- API retry mechanism with exponential backoff
- Configuration management via `~/.lazycommitrc`
- Rich terminal UI with progress indicators
- Conventional Commits format support
- Dry-run mode for previewing changes
- Verbose output mode
- File monitoring module (watchfiles integration)

### Features
- Detects and warns about unsafe git states
- Automatic rollback on push failure
- Supports custom API base URLs for alternative LLM providers
- Configurable token limits and context size
- Progress indicators for all long-running operations

[Unreleased]: https://github.com/nrmlthms/lazycommit/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/nrmlthms/lazycommit/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/nrmlthms/lazycommit/releases/tag/v0.1.0
