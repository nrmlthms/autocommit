# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI/CD workflows for testing, linting, type checking, and security scanning
- PyPI publishing workflow for releases

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

[Unreleased]: https://github.com/nrmlthms/autocommit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nrmlthms/autocommit/releases/tag/v0.1.0
