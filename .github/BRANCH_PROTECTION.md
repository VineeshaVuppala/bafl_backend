# Branch Protection Configuration

This document describes how to configure branch protection rules for the main branch to enforce the CI/CD workflow and prevent direct pushes.

## GitHub Branch Protection Settings

To configure branch protection rules for the `main` branch:

### Step 1: Navigate to Branch Protection Settings

1. Go to your repository on GitHub
2. Click on **Settings** tab
3. Click on **Branches** in the left sidebar
4. Under "Branch protection rules", click **Add rule** or edit existing rule for `main`

### Step 2: Configure Protection Rules

Configure the following settings:

#### Basic Settings

- **Branch name pattern**: `main`
- ✅ **Require a pull request before merging**
  - ✅ **Require approvals**: Set to at least 1 approval
  - ✅ **Dismiss stale pull request approvals when new commits are pushed**
  - ✅ **Require review from Code Owners** (optional, if you have a CODEOWNERS file)

#### Status Checks

- ✅ **Require status checks to pass before merging**
  - ✅ **Require branches to be up to date before merging**
  - **Required status checks** (select all that must pass):
    - `Code Quality & Linting`
    - `Run Tests (3.9)`
    - `Run Tests (3.10)`
    - `Run Tests (3.11)`
    - `Security Scanning`
    - `Deploy to Staging`
    - `Run Integration Tests`

#### Additional Settings

- ✅ **Require conversation resolution before merging**
- ✅ **Require signed commits** (optional, for extra security)
- ✅ **Require linear history** (optional, to keep history clean)
- ✅ **Include administrators** (enforce rules for repository admins too)
- ✅ **Restrict who can push to matching branches**
  - Select: No one (this prevents direct pushes)
  - Or specify specific teams/users who can push in emergencies
- ✅ **Allow force pushes**: Disabled
- ✅ **Allow deletions**: Disabled

### Step 3: Save Changes

Click **Create** or **Save changes** to apply the branch protection rules.

## What These Rules Enforce

With these settings enabled:

1. **No Direct Pushes**: No one can push directly to the `main` branch
2. **Pull Requests Required**: All changes must go through a pull request
3. **Automated Testing**: All CI/CD checks must pass before merge
4. **Code Review**: At least one approval is required before merge
5. **Staging Deployment**: Code is automatically deployed to staging when PR is created
6. **Integration Tests**: Integration tests run against staging environment
7. **Production Deployment**: Code is automatically deployed to production after merge

## CI/CD Workflow

### On Pull Request Creation/Update

```
1. Code Quality & Linting
   ├── Black formatting check
   ├── isort import sorting check
   └── Flake8 linting

2. Run Tests (Python 3.9, 3.10, 3.11)
   ├── Unit tests with pytest
   ├── Coverage reporting
   └── Upload coverage to Codecov

3. Security Scanning
   ├── Safety (dependency vulnerabilities)
   └── Bandit (code security issues)

4. Deploy to Staging
   ├── Deploy application
   ├── Run smoke tests
   └── Comment PR with staging URL

5. Run Integration Tests
   └── Test all endpoints on staging
```

### On Merge to Main

```
1. All PR checks must have passed

2. Deploy to Production
   ├── Deploy application
   ├── Run smoke tests
   └── Create deployment notification
```

## Environment Setup

### Required GitHub Secrets

Configure these secrets in **Settings > Secrets and variables > Actions**:

#### Staging Environment
- `STAGING_DEPLOY_KEY` - SSH key or API token for staging deployment
- `STAGING_SERVER_URL` - URL of staging server
- `STAGING_DB_CONNECTION` - Database connection string for staging

#### Production Environment
- `PRODUCTION_DEPLOY_KEY` - SSH key or API token for production deployment
- `PRODUCTION_SERVER_URL` - URL of production server
- `PRODUCTION_DB_CONNECTION` - Database connection string for production

#### Optional Secrets
- `CODECOV_TOKEN` - Token for uploading coverage reports
- `SLACK_WEBHOOK` - For deployment notifications
- `AWS_ACCESS_KEY_ID` - If deploying to AWS
- `AWS_SECRET_ACCESS_KEY` - If deploying to AWS

## Troubleshooting

### Status Check Not Appearing

If a required status check is not appearing:
1. Run the workflow at least once by creating a test PR
2. The status check names will then be available to select
3. Edit the branch protection rule and add the new checks

### Emergency Access

If you need to make an emergency hotfix:
1. Create a hotfix branch from `main`
2. Make the fix and create a PR
3. Request expedited review
4. Merge after all checks pass

Or temporarily:
1. Modify branch protection rules to exclude administrators
2. Push your fix
3. Re-enable the rules immediately after

### Bypass Protection (Not Recommended)

Only use in extreme emergencies:
1. Go to branch protection settings
2. Temporarily disable protection rules
3. Push your changes
4. **Immediately re-enable protection rules**

## Best Practices

1. **Never disable branch protection permanently**
2. **Keep PRs small and focused** - easier to review and test
3. **Write meaningful commit messages** - helps with debugging
4. **Run tests locally** before pushing - saves CI/CD time
5. **Review staging deployment** before approving PR
6. **Monitor production deployment** after merge
7. **Set up notifications** for failed deployments

## Additional Resources

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Environments Documentation](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
