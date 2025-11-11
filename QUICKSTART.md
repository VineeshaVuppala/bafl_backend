# Quick Start Guide

Get started with the BAFL Backend repository in minutes!

## 🚀 First Time Setup (5 minutes)

### 1. Configure Branch Protection

**This is the most important step!**

1. Go to: `https://github.com/rkajaria-1507/BAFL-Backend/settings/branches`
2. Click **Add rule** (or edit `main` rule)
3. Set **Branch name pattern**: `main`
4. Enable these settings:
   - ✅ Require a pull request before merging (1 approval)
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date
   - ✅ Require conversation resolution
   - ✅ Include administrators
   - ✅ Restrict who can push (leave empty = no one)
   - ❌ Allow force pushes (keep disabled)
   - ❌ Allow deletions (keep disabled)
5. Click **Create** or **Save**

> **Note**: You'll need to add required status checks after your first PR runs. See [SETUP_GUIDE.md](.github/SETUP_GUIDE.md) for details.

### 2. Enable GitHub Actions (if not already enabled)

1. Go to: `https://github.com/rkajaria-1507/BAFL-Backend/settings/actions`
2. Under "Actions permissions", select **Allow all actions and reusable workflows**
3. Under "Workflow permissions", select **Read and write permissions**
4. Check **Allow GitHub Actions to create and approve pull requests**
5. Click **Save**

### 3. Test the Pipeline

```bash
# Clone the repository
git clone https://github.com/rkajaria-1507/BAFL-Backend.git
cd BAFL-Backend

# Create a test branch
git checkout -b test/initial-test

# Make a small change
echo "# Pipeline Test" >> test.txt
git add test.txt
git commit -m "Test CI/CD pipeline"
git push origin test/initial-test
```

4. Go to GitHub and create a PR from `test/initial-test` to `main`
5. Watch the Actions tab - all checks should run
6. After checks pass, add required status checks to branch protection (see Step 1)
7. Get the PR approved and merge it

**That's it! Your pipeline is now active! 🎉**

---

## 📝 Daily Workflow

### Making Changes

```bash
# 1. Get latest code
git checkout main
git pull origin main

# 2. Create feature branch
git checkout -b feature/my-feature

# 3. Make changes
# ... edit files ...

# 4. Test locally
pytest tests/
black --check .
isort --check-only .
flake8 .

# 5. Commit and push
git add .
git commit -m "Add my feature"
git push origin feature/my-feature

# 6. Create PR on GitHub
# All CI/CD checks will run automatically
```

### What Happens Automatically

When you create a PR:
- ✅ Code is linted and formatted checks run
- ✅ Tests run on Python 3.9, 3.10, and 3.11
- ✅ Security scans check for vulnerabilities
- ✅ Code deploys to staging environment
- ✅ Integration tests run on staging
- 💬 PR gets a comment with staging URL

After PR is approved and merged:
- ✅ Code deploys to production automatically
- ✅ Smoke tests run on production
- 📢 Deployment notification is sent

---

## 🛠️ Local Development

### Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run Tests

```bash
pytest                      # Run all tests
pytest -v                   # Verbose output
pytest --cov=. --cov-report=html  # With coverage
```

### Code Quality

```bash
black .                     # Format code
isort .                     # Sort imports
flake8 .                    # Lint code
```

---

## 🔧 Customization Needed

Before using in production, update these files:

### 1. Deployment Scripts
Edit `scripts/deploy-staging.sh` and `scripts/deploy-production.sh`:
- Uncomment and configure your deployment method
- Add your server URLs
- Configure database migrations
- Add health check endpoints

### 2. CI/CD Workflow
Edit `.github/workflows/ci-cd.yml`:
- Update deployment steps with your actual deployment commands
- Configure staging and production URLs
- Add environment-specific configurations

### 3. GitHub Secrets
Add these in: Settings → Secrets and variables → Actions
- `STAGING_DEPLOY_KEY`
- `STAGING_SERVER_URL`
- `PRODUCTION_DEPLOY_KEY`
- `PRODUCTION_SERVER_URL`
- Any other deployment credentials

### 4. Tests
Replace sample tests in `tests/test_sample.py` with your actual tests:
- Add tests for your API endpoints
- Add integration tests
- Add database tests
- Maintain good test coverage

### 5. Dependencies
Update `requirements.txt` with your application dependencies:
```txt
# Example for Flask
flask==3.0.0
flask-sqlalchemy==3.1.0
flask-migrate==4.0.0

# Example for FastAPI
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.0
```

---

## 📚 Additional Documentation

- [CI/CD Setup Guide](CI_CD_SETUP.md) - Complete CI/CD and development workflow guide
- [Complete Setup Guide](.github/SETUP_GUIDE.md) - Detailed configuration steps
- [Branch Protection Details](.github/BRANCH_PROTECTION.md) - All protection rules explained
- [README.md](README.md) - Project overview

---

## 🆘 Need Help?

### Common Issues

**Q: Can't push to main**
- ✅ This is correct! Create a PR instead.

**Q: Status checks don't appear in branch protection**
- Create and run a PR first to make them available.

**Q: Tests fail in CI but pass locally**
- Check Python version (CI tests on 3.9, 3.10, 3.11).
- Verify all dependencies are in `requirements.txt`.

**Q: Deployment fails**
- Configure deployment scripts for your platform.
- Add required secrets in GitHub settings.
- Check deployment logs in Actions tab.

### Get More Help

1. Check [SETUP_GUIDE.md](.github/SETUP_GUIDE.md) for detailed troubleshooting
2. Review GitHub Actions logs for specific errors
3. Create an issue in the repository

---

**You're all set! Happy coding! 🚀**
