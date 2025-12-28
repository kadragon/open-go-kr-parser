# Coding Style Guide

## Python Version
- Python 3.11+

## Code Formatting
- **Formatter:** Black (line-length: 88)
- **Linter:** Ruff
- **Type Hints:** Required for all public functions

## Naming Conventions
- **Modules:** snake_case (e.g., `api_client.py`)
- **Classes:** PascalCase (e.g., `OpenGoKrClient`)
- **Functions:** snake_case (e.g., `fetch_documents`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `API_BASE_URL`)

## Project Structure
- Source code in `src/open_go_kr_parser/`
- Tests in `tests/` mirroring source structure
- Configuration in `config/`

## Documentation
- Docstrings: Google style
- Type hints in function signatures

## Dependencies
- Use `pyproject.toml` for dependency management
- Prefer standard library when possible
- Minimize external dependencies
