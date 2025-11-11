# BAFL-Backend

This is the backend for the BAFL website for the admins and coaches.

## 🚀 CI/CD Pipeline & Branch Protection

This repository is configured with a comprehensive CI/CD pipeline that ensures code quality, security, and automated deployments.

### Key Features

- ✅ **Branch Protection**: Main branch is protected - no direct pushes allowed
- ✅ **Automated Testing**: All code is tested before merge
- ✅ **Code Quality Checks**: Linting and formatting validation
- ✅ **Security Scanning**: Automated vulnerability detection
- ✅ **Staging Deployment**: Automatic deployment to staging on PR creation
- ✅ **Integration Tests**: Full endpoint testing on staging environment
- ✅ **Production Deployment**: Automatic deployment to production after merge

## 📋 Development Workflow

### 1. Creating a Pull Request

```bash
# Create a new branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# Make your changes
# ... code changes ...

# Commit and push
git add .
git commit -m "Description of your changes"
git push origin feature/your-feature-name
```

### 2. Automated CI/CD Process

When you create a pull request, the following happens automatically:

```
1. Code Quality & Linting (Required ✓)
   ├── Black formatting check
   ├── isort import sorting check
   └── Flake8 linting

2. Run Tests - Python 3.9, 3.10, 3.11 (Required ✓)
   ├── Unit tests with pytest
   ├── Coverage reporting
   └── Upload coverage to Codecov

3. Security Scanning (Required ✓)
   ├── Safety (dependency vulnerabilities)
   └── Bandit (code security issues)

4. Deploy to Staging (Required ✓)
   ├── Deploy application to staging
   ├── Run smoke tests
   └── Comment PR with staging URL

5. Run Integration Tests (Required ✓)
   └── Test all endpoints on staging environment
```

All checks must pass ✅ before the PR can be merged into main.

### 3. Merging to Main

After all checks pass and the PR is approved:

1. PR is merged into main branch
2. Production deployment automatically triggers
3. Application is deployed to production
4. Smoke tests run on production
5. Deployment notification is sent

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/rkajaria-1507/BAFL-Backend.git
cd BAFL-Backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linting
black --check .
isort --check-only .
flake8 .
```

## 🔒 Branch Protection Configuration

The main branch is protected with the following rules:

- **No direct pushes** - all changes must go through pull requests
- **Require pull request reviews** - at least 1 approval required
- **Require status checks to pass** - all CI/CD checks must pass
- **Require branches to be up to date** - must be up-to-date with main
- **Require conversation resolution** - all comments must be resolved

For detailed configuration instructions, see [Branch Protection Guide](.github/BRANCH_PROTECTION.md).

## 🧪 Testing

### Running Tests Locally

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_sample.py

# Run with verbose output
pytest -v
```

### Test Structure

```
tests/
├── __init__.py
├── test_sample.py          # Sample tests (replace with your tests)
└── integration/            # Integration tests (create as needed)
```

## 📦 Deployment

### Staging Deployment

Staging deployment happens automatically when a pull request is created:

```bash
# Deployment is triggered automatically on PR creation
# Manual deployment (if needed):
./scripts/deploy-staging.sh
```

### Production Deployment

Production deployment happens automatically when changes are merged to main:

```bash
# Deployment is triggered automatically on merge
# Manual deployment (if needed):
./scripts/deploy-production.sh
```

## 🔧 Configuration Files

### GitHub Actions Workflow
- `.github/workflows/ci-cd.yml` - Main CI/CD pipeline configuration

### Testing Configuration
- `pytest.ini` - Pytest configuration
- `pyproject.toml` - Black, isort, and coverage configuration
- `.flake8` - Flake8 linting configuration

### Dependencies
- `requirements.txt` - Production dependencies
- `requirements-dev.txt` - Development dependencies

### Deployment Scripts
- `scripts/deploy-staging.sh` - Staging deployment script
- `scripts/deploy-production.sh` - Production deployment script

## 📚 Additional Documentation

- [Branch Protection Setup](.github/BRANCH_PROTECTION.md) - Detailed branch protection configuration
- [CI/CD Workflow](.github/workflows/ci-cd.yml) - Complete workflow definition

## 🤝 Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Ensure all tests pass locally
4. Run code quality checks locally
5. Create a pull request
6. Wait for all automated checks to pass
7. Request review from team members
8. Address review comments
9. Merge after approval and passing checks

## 📝 Code Quality Standards

This project enforces the following code quality standards:

- **Black** for code formatting (line length: 127)
- **isort** for import sorting
- **Flake8** for linting
- **pytest** for testing (minimum coverage target)
- **Bandit** for security scanning
- **Safety** for dependency vulnerability checking

## 🔐 Security

- All dependencies are scanned for vulnerabilities
- Code is scanned for security issues with Bandit
- Secrets should never be committed to the repository
- Use environment variables for sensitive configuration

## 📞 Support

For questions or issues:
1. Check existing issues on GitHub
2. Create a new issue with detailed description
3. Contact the development team

## 📄 License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.
