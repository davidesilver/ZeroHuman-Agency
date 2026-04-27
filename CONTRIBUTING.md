# Contributing to Content Engine

Thank you for your interest in contributing to Content Engine! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and collaborative. We expect all contributors to adhere to these principles:

- Treat others with respect and professionalism
- Welcome newcomers and help them learn
- Focus on constructive feedback and solutions
- Respect different viewpoints and experiences

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for Python package management
- A Supabase project for local development

### Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/ZeroHuman-Agency.git`
3. Navigate to the project: `cd ZeroHuman-Agency`
4. Install frontend dependencies: `npm install`
5. Install backend dependencies: `cd python && uv sync && cd ..`
6. Copy environment template: `cp .env.example .env.local`
7. Fill in your environment variables
8. Set up Supabase locally: `supabase link --project-ref YOUR_PROJECT_REF`
9. Apply migrations: `supabase db push`

## Development Workflow

### Branch Naming

Use clear branch names:
- `feat/feature-name` for new features
- `fix/bug-name` for bug fixes
- `docs/update-name` for documentation updates
- `refactor/component-name` for code refactoring

### Making Changes

1. Create a new branch from `main`: `git checkout -b feat/your-feature`
2. Make your changes
3. Write tests if applicable
4. Ensure all tests pass: `npm test && cd python && uv run pytest`
5. Run linting: `npm run lint`
6. Commit with clear messages: `git commit -m "feat: add new feature"`

### Commit Messages

Follow conventional commits format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Example: `feat: add support for new image generation backend`

## Testing

### Frontend Tests

```bash
npm test
```

### Backend Tests

```bash
cd python
uv run pytest
```

### Integration Tests

```bash
cd python
uv run pytest tests/integration/
```

## Code Style

### Frontend

- Use TypeScript for type safety
- Follow existing component patterns
- Use Tailwind CSS for styling
- Run linter: `npm run lint`

### Backend

- Follow PEP 8 style guide
- Use type hints
- Write docstrings for functions and classes
- Run linter: `cd python && uv run ruff check`

## Submitting Changes

1. Push your branch: `git push origin feat/your-feature`
2. Create a pull request on GitHub
3. Fill in the PR template
4. Wait for code review
5. Address feedback if needed
6. PR will be merged when approved

## Documentation

- Update README.md for user-facing changes
- Update relevant docs/ files for technical changes
- Add comments for complex logic
- Keep documentation in sync with code changes

## Issues

- Search existing issues before creating new ones
- Use issue templates when available
- Provide clear steps to reproduce bugs
- Include environment details and error messages

## Questions?

- Open an issue for questions or discussions
- Check existing documentation first
- Be patient - maintainers volunteer their time

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
