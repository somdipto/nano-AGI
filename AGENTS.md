# AGENTS.md - memU Development Guide

This guide helps AI agents work effectively in the memU repository.

## Project Overview

memU is an AI memory framework for 24/7 proactive agents. It's a hybrid Python/Rust project using PyO3 for Python bindings.

- **Language**: Python 3.13+ with Rust extensions
- **Build System**: Maturin (for Rust/Python bindings)
- **Package Manager**: uv
- **Project Layout**: src/ layout with `src/memu/` as main package

## Build/Test/Lint Commands

### Setup
```bash
# Install dependencies and setup environment
make install
# Or manually:
uv sync
uv run pre-commit install
```

### Running Tests
```bash
# Run all tests with coverage
make test
# Or manually:
uv run python -m pytest --cov --cov-config=pyproject.toml --cov-report=xml

# Run single test file
uv run python -m pytest tests/test_sqlite.py

# Run single test
uv run python -m pytest tests/test_sqlite.py::test_function_name

# Run tests matching pattern
uv run python -m pytest -k "test_name_pattern"
```

### Linting & Type Checking
```bash
# Run all checks (lock file, pre-commit, mypy, deptry)
make check

# Individual commands:
# Check lock file consistency
uv lock --locked

# Run pre-commit hooks on all files
uv run pre-commit run -a

# Static type checking
uv run mypy

# Check for obsolete dependencies
uv run deptry src
```

### Code Formatting
```bash
# Format with ruff
uv run ruff format .

# Lint and auto-fix with ruff
uv run ruff check --fix .
```

### Building Rust Extension
```bash
# Build the Rust extension (done automatically by maturin during uv sync)
uv run maturin develop
```

## Code Style Guidelines

### Imports
- Use `from __future__ import annotations` at the top of all Python files
- Group imports: stdlib → third-party → local (memu)
- Use absolute imports from `memu` package
- Use `from collections.abc` for abstract base classes (Awaitable, Callable, Mapping)
- Use `from typing` for type hints (Any, TYPE_CHECKING, cast, get_args)

Example:
```python
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from memu.database.models import MemoryCategory
```

### Formatting
- **Line length**: 120 characters (configured in pyproject.toml)
- **Formatter**: ruff (preview mode enabled)
- **Quote style**: Follow ruff defaults
- **Trailing commas**: Use trailing commas in multi-line structures

### Type Hints
- **Required**: Strict typing enforced via mypy
- Always type function parameters and return types
- Use `dict[str, Any]` instead of `Dict[str, Any]` (Python 3.9+ syntax)
- Use `|` for unions instead of `typing.Union` (e.g., `str | None`)
- Use `TYPE_CHECKING` block for imports only needed for type hints
- Cast return values with `cast()` when type inference fails

### Naming Conventions
- **Classes**: PascalCase (e.g., `MemoryService`, `WorkflowStep`)
- **Functions/methods**: snake_case (e.g., `list_memory_items`)
- **Private methods**: Leading underscore (e.g., `_build_workflow`)
- **Constants**: UPPER_CASE (e.g., `CATEGORY_PATCH_PROMPT`)
- **Variables**: snake_case, descriptive names
- **Type variables**: Descriptive names, often with suffix like `_type`

### Error Handling
- Use specific exception types (ValueError, RuntimeError)
- Create error messages as variables before raising:
  ```python
  msg = "Invalid memory type: '{memory_type}'"
  raise ValueError(msg)
  ```
- Use early returns to reduce nesting
- Validate inputs at function start

### Function Design
- Keep functions focused and single-purpose
- Use keyword-only arguments for clarity with `*`:
  ```python
  async def create_memory_item(
      self,
      *,
      memory_type: MemoryType,
      memory_content: str,
      user: dict[str, Any] | None = None,
  ) -> dict[str, Any]:
  ```
- Document complex logic with inline comments

### Documentation
- Add module-level docstrings explaining purpose
- Use descriptive variable names over comments
- Document workflow steps and their roles

### Testing
- Tests located in `tests/` directory
- Use pytest with asyncio support
- Test files follow pattern `test_*.py`
- Async tests use `async def` with pytest-asyncio
- Use fixtures from `tests/__init__.py` where available

## Project Structure

```
src/memu/
├── __init__.py           # Package entry, exports from _core
├── _core.pyi            # Type stubs for Rust extension
├── app/                 # Main application logic
│   ├── service.py       # MemoryService main class
│   ├── crud.py          # CRUD operations mixin
│   ├── memorize.py      # Memory creation logic
│   ├── retrieve.py      # Retrieval logic
│   ├── patch.py         # Memory patching
│   └── settings.py      # Configuration models
├── workflow/            # Workflow engine
│   ├── step.py          # WorkflowStep definition
│   ├── runner.py        # Workflow execution
│   ├── pipeline.py      # Pipeline management
│   └── interceptor.py   # Step interception
├── database/            # Database layer
│   ├── postgres/        # PostgreSQL backend
│   └── state.py         # Database state management
├── llm/                 # LLM client wrappers
│   ├── wrapper.py       # Main LLM wrapper
│   ├── openai_sdk.py    # OpenAI SDK integration
│   ├── http_client.py   # HTTP client
│   └── backends/        # Provider backends
├── prompts/             # LLM prompts
│   ├── retrieve/        # Retrieval prompts
│   ├── preprocess/      # Preprocessing prompts
│   └── memory_type/     # Memory type prompts
└── utils/               # Utilities
    ├── conversation.py  # Conversation utilities
    └── video.py         # Video processing

tests/                   # Test suite
examples/                # Usage examples
```

## Common Tasks

### Adding a New LLM Backend
1. Create file in `src/memu/llm/backends/`
2. Inherit from base backend class
3. Implement required methods
4. Add tests in `tests/llm/`

### Adding a New Prompt
1. Create file in appropriate `src/memu/prompts/` subdirectory
2. Define prompt as constant with UPPER_CASE name
3. Add type hints for prompt inputs
4. Update `__init__.py` exports

### Adding Database Operations
1. Add repository methods in appropriate `src/memu/database/` file
2. Add CRUD methods in `src/memu/app/crud.py` mixin
3. Create workflow steps for complex operations
4. Add corresponding tests

## CI/CD

GitHub Actions runs on push/PR:
1. `uv sync --frozen` - Install deps
2. `uv run make check` - Linting & type checks
3. `uv run make test` - Run test suite

## Dependencies

- **Core**: pydantic, sqlmodel, alembic, httpx, openai
- **Rust**: pyo3 for Python bindings
- **Dev**: ruff, mypy, pytest, pre-commit
- **Docs**: mkdocs, mkdocstrings

Always update `pyproject.toml` for dependencies, never requirements.txt.
