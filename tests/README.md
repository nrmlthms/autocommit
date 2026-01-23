# Test Suite for LazyCommit

This directory contains the test suite for LazyCommit, organized into unit tests, integration tests, and fixtures.

## Structure

```
tests/
├── unit/                   # Unit tests for individual components
│   ├── test_config.py      # Tests for Config class
│   ├── test_detector.py    # Tests for ChangeDetector
│   ├── test_generator.py   # Tests for LLMCommitMessageGenerator
│   └── test_core.py        # Tests for AutoCommit core
├── integration/            # Integration tests for complete workflows
│   └── test_end_to_end.py  # End-to-end workflow tests
├── fixtures/               # Shared test fixtures
│   └── git_scenarios.py    # Git repository fixtures
├── conftest.py             # Pytest configuration and shared fixtures
└── README.md               # This file
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run unit tests only
```bash
pytest tests/unit/
```

### Run integration tests only
```bash
pytest tests/integration/
```

### Run specific test file
```bash
pytest tests/unit/test_config.py
```

### Run specific test
```bash
pytest tests/unit/test_config.py::TestConfig::test_default_config
```

### Run tests with coverage
```bash
pytest --cov=lazycommit --cov-report=html
```

### Run tests in verbose mode
```bash
pytest -v
```

### Run tests with markers
```bash
pytest -m unit          # Run only unit tests
pytest -m integration   # Run only integration tests
pytest -m "not slow"    # Skip slow tests
```

## Test Categories

### Unit Tests
Test individual components in isolation with mocked dependencies:
- **test_config.py**: Configuration loading, validation, and environment variables
- **test_detector.py**: Git change detection, file status parsing, staging/unstaging
- **test_generator.py**: LLM message generation, token estimation, parameter validation
- **test_core.py**: AutoCommit workflow, commit creation, message validation

### Integration Tests
Test complete workflows with real git repositories:
- **test_end_to_end.py**: Full commit workflows, safe mode, dry run, error handling

### Fixtures
Reusable test fixtures for different scenarios:
- **git_scenarios.py**: Various git repository states (empty, with commits, with changes, etc.)

## Writing New Tests

### Adding Unit Tests
1. Create test file in `tests/unit/` following naming convention `test_*.py`
2. Import the module to test
3. Use pytest fixtures for setup/teardown
4. Mock external dependencies
5. Use descriptive test names: `test_<what>_<condition>_<expected>`

Example:
```python
def test_config_validation_invalid_temperature_raises_error() -> None:
    config = Config(temperature=-0.1)
    with pytest.raises(ValueError):
        validate_config(config)
```

### Adding Integration Tests
1. Use git repository fixtures from `git_scenarios.py`
2. Test complete workflows end-to-end
3. Verify actual git state changes
4. Use mocked LLM responses to avoid API calls

### Adding Fixtures
1. Add to `tests/fixtures/git_scenarios.py`
2. Use `@pytest.fixture` decorator
3. Yield the fixture value
4. Cleanup happens after yield automatically

## Test Coverage

Current test coverage includes:
- ✅ Config loading and validation
- ✅ Change detection (staged, unstaged, untracked)
- ✅ LLM message generation with mocked API
- ✅ Commit creation and validation
- ✅ Safe mode with backup branches
- ✅ Dry run mode
- ✅ Error handling and fallbacks
- ✅ Token estimation and cost warnings
- ✅ Parameter validation

## Dependencies

Required for running tests:
- pytest >= 7.0.0
- git (command-line tool)

Optional:
- pytest-cov (for coverage reports)
- pytest-xdist (for parallel test execution)

Install test dependencies:
```bash
pip install pytest pytest-cov pytest-xdist
```

## CI/CD

Tests can be run in CI/CD pipelines:
```yaml
- name: Run tests
  run: |
    pip install -e ".[dev]"
    pytest --cov=lazycommit --cov-report=xml
```

## Troubleshooting

### Git not found
Ensure git is installed and available in PATH:
```bash
git --version
```

### Import errors
Ensure the package is installed in development mode:
```bash
pip install -e .
```

### Test isolation issues
Each test that modifies git state should use a fresh fixture to avoid interference between tests.
