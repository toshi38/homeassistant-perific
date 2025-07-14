# Contributing to Perific Home Assistant Integration

Thank you for your interest in contributing to this project! This document provides guidelines for contributing to the Perific Home Assistant integration.

## Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/homeassistant-perific.git
   cd homeassistant-perific
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install homeassistant  # For integration testing
   ```

3. **Set up Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Perific credentials
   ```

## Testing

### Local Testing
```bash
# Test standalone API
python test_api_standalone.py

# Test with mocks (CI mode)
CI=true python test_api_standalone_mock.py
```

### Home Assistant Testing
1. Copy `custom_components/perific/` to your Home Assistant config directory
2. Restart Home Assistant
3. Add the integration via UI

## Code Quality

This project uses GitHub Actions for continuous integration. All pull requests must pass:

- **Linting**: Code formatting with `black` and `isort`
- **Testing**: Automated tests with mocks
- **Integration Validation**: Home Assistant integration structure checks
- **Manifest Validation**: Ensures proper manifest.json format

### Running Locally
```bash
# Format code
black .
isort .

# Lint
flake8 .
```

## Pull Request Process

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation if needed

3. **Test Your Changes**
   - Run local tests
   - Test in Home Assistant if applicable

4. **Submit Pull Request**
   - Target the `main` branch
   - Provide clear description of changes
   - Link any related issues

## Branch Protection

The `main` branch is protected with the following rules:

### Required Status Checks
- **Lint & Format**: Code must pass formatting and linting
- **Test**: All tests must pass
- **Integration Check**: Home Assistant integration must be valid
- **Manifest Validation**: manifest.json must be properly formatted

### Protection Rules
- Pull request reviews required before merging
- Stale reviews dismissed when new commits are pushed
- Status checks must pass before merging
- Linear history required (no merge commits)

## GitHub Secrets

For CI to work with real API testing, the following secrets should be configured:

- `PERIFIC_EMAIL`: Your Perific account email
- `PERIFIC_TOKEN`: Your Perific API token

## Setting Up Branch Protection

Repository administrators should configure branch protection rules:

1. Go to **Settings → Branches**
2. **Add protection rule** for `main` branch
3. Configure:
   - ✅ **Require pull request reviews before merging**
   - ✅ **Dismiss stale pull request approvals when new commits are pushed**
   - ✅ **Require status checks to pass before merging**
   - ✅ **Require branches to be up to date before merging**
   - ✅ **Require linear history**
   - ✅ **Include administrators**

### Required Status Checks
Add these status checks:
- `Lint & Format`
- `Test`
- `Integration Check`
- `Manifest Validation`

## Automated Dependencies

Dependabot is configured to automatically update Python dependencies weekly. These updates will:
- Create pull requests for dependency updates
- Assign to `@toshi38` for review
- Include proper commit message prefixes

## Code Style Guidelines

- Use `black` for code formatting
- Use `isort` for import sorting
- Follow PEP 8 style guidelines
- Add type hints where appropriate
- Include docstrings for public functions

## Questions?

If you have questions about contributing, please:
1. Check existing issues
2. Create a new issue for discussion
3. Reach out to maintainers

Thank you for contributing!