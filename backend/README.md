
# Backend Test Coverage and Execution

This backend uses **pytest** and related plugins to ensure high test coverage.

### Running Tests

To run all backend tests and measure coverage:

```bash
cd backend
uv run pytest --cov=src --cov-report=term-missing
```

### Frameworks Used
- **pytest**: Unit testing
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking utilities

### Coverage Target
Minimum coverage is **70%** as per project guidelines.
