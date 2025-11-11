# Complete Setup Guide for CI/CD Pipeline

This guide walks you through the complete setup of the CI/CD pipeline and branch protection for the BAFL-Backend repository.

## Table of Contents

1. [Repository Configuration](#1-repository-configuration)
2. [Branch Protection Setup](#2-branch-protection-setup)
3. [GitHub Actions Secrets](#3-github-actions-secrets)
4. [Environment Configuration](#4-environment-configuration)
5. [Testing the Pipeline](#5-testing-the-pipeline)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Repository Configuration

### 1.1 Enable GitHub Actions

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Actions** → **General**
3. Under "Actions permissions", select **Allow all actions and reusable workflows**
4. Click **Save**

### 1.2 Enable Issues

1. Go to **Settings** → **General**
2. Under "Features", ensure **Issues** is checked
3. This allows linking PRs to issues

---

## 2. Branch Protection Setup

### 2.1 Navigate to Branch Protection

1. Go to **Settings** → **Branches**
2. Click **Add rule** (or edit existing rule for `main`)

### 2.2 Configure Branch Name Pattern

- **Branch name pattern**: `main`

### 2.3 Configure Protection Rules

#### ✅ Require Pull Request Reviews
- Check **Require a pull request before merging**
- Check **Require approvals**: Set to `1` (or more)
- Check **Dismiss stale pull request approvals when new commits are pushed**
- Check **Require review from Code Owners** (optional)

#### ✅ Require Status Checks
- Check **Require status checks to pass before merging**
- Check **Require branches to be up to date before merging**
- In the search box, add these required status checks:
  - `Code Quality & Linting`
  - `Run Tests (3.9)` 
  - `Run Tests (3.10)`
  - `Run Tests (3.11)`
  - `Security Scanning`
  - `Deploy to Staging`
  - `Run Integration Tests`

> **Note**: Status checks will only appear in the list after they've run at least once. Create a test PR first to make them available.

#### ✅ Additional Settings
- Check **Require conversation resolution before merging**
- Check **Require signed commits** (optional)
- Check **Require linear history** (optional)
- Check **Include administrators** (recommended)

#### ✅ Restrict Push Access
- Check **Restrict who can push to matching branches**
- Leave the selection empty (no one can push directly)

#### ✅ Additional Restrictions
- **Allow force pushes**: Leave unchecked ❌
- **Allow deletions**: Leave unchecked ❌

### 2.4 Save the Rule

Click **Create** or **Save changes**

---

## 3. GitHub Actions Secrets

Configure secrets for deployment and integrations.

### 3.1 Navigate to Secrets

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**

### 3.2 Required Secrets

Add the following secrets as needed for your deployment:

#### Staging Environment Secrets

```
STAGING_DEPLOY_KEY          # SSH key or API token for staging deployment
STAGING_SERVER_URL          # URL of staging server
STAGING_DB_CONNECTION       # Database connection string (if applicable)
```

#### Production Environment Secrets

```
PRODUCTION_DEPLOY_KEY       # SSH key or API token for production deployment
PRODUCTION_SERVER_URL       # URL of production server
PRODUCTION_DB_CONNECTION    # Database connection string (if applicable)
```

#### Optional Secrets

```
CODECOV_TOKEN               # For uploading coverage reports
SLACK_WEBHOOK               # For Slack notifications
DISCORD_WEBHOOK             # For Discord notifications
AWS_ACCESS_KEY_ID           # If deploying to AWS
AWS_SECRET_ACCESS_KEY       # If deploying to AWS
HEROKU_API_KEY              # If deploying to Heroku
```

### 3.3 Add Each Secret

For each secret:
1. Click **New repository secret**
2. Enter the **Name** (e.g., `STAGING_DEPLOY_KEY`)
3. Enter the **Value**
4. Click **Add secret**

---

## 4. Environment Configuration

### 4.1 Create Environments

1. Go to **Settings** → **Environments**
2. Click **New environment**

### 4.2 Configure Staging Environment

1. **Name**: `staging`
2. **Protection rules** (optional):
   - Add required reviewers if you want manual approval for staging
3. **Environment secrets**: Add staging-specific secrets here instead of repository secrets (more secure)
4. Click **Configure environment**

### 4.3 Configure Production Environment

1. **Name**: `production`
2. **Protection rules** (recommended):
   - Check **Required reviewers** and add 1-2 reviewers
   - This adds manual approval before production deployment
3. **Environment secrets**: Add production-specific secrets
4. Click **Configure environment**

### 4.4 Environment Variables

Add environment variables if needed:
- `ENVIRONMENT_NAME`
- `API_URL`
- `DEBUG_MODE`
- etc.

---

## 5. Testing the Pipeline

### 5.1 Create a Test Pull Request

```bash
# Create a test branch
git checkout -b test/pipeline-setup
git push origin test/pipeline-setup

# Make a small change
echo "# Test" >> test.txt
git add test.txt
git commit -m "Test CI/CD pipeline"
git push origin test/pipeline-setup
```

### 5.2 Open Pull Request

1. Go to GitHub and create a pull request from `test/pipeline-setup` to `main`
2. Watch the Actions tab for workflow execution

### 5.3 Verify Checks

Ensure all checks run and pass:
- ✅ Code Quality & Linting
- ✅ Run Tests (3.9)
- ✅ Run Tests (3.10)
- ✅ Run Tests (3.11)
- ✅ Security Scanning
- ✅ Deploy to Staging
- ✅ Run Integration Tests

### 5.4 Check Branch Protection

Try to push directly to main (should fail):
```bash
git checkout main
echo "test" >> direct-push-test.txt
git add direct-push-test.txt
git commit -m "Test direct push"
git push origin main
# This should be rejected by branch protection
```

### 5.5 Complete Test Merge

1. Get approval on your test PR
2. Merge the PR
3. Watch production deployment run
4. Verify production deployment succeeds

---

## 6. Troubleshooting

### Issue: Status Checks Not Appearing

**Problem**: Required status checks don't appear in branch protection settings.

**Solution**: 
1. Create and merge at least one PR to trigger all workflows
2. After workflows run, status checks will appear in the list
3. Edit branch protection and add them

### Issue: Workflow Fails with Permission Error

**Problem**: Workflow can't write comments or create deployment status.

**Solution**:
1. Go to **Settings** → **Actions** → **General**
2. Under "Workflow permissions", select **Read and write permissions**
3. Check **Allow GitHub Actions to create and approve pull requests**
4. Save changes

### Issue: Secrets Not Available in Workflow

**Problem**: Workflow can't access secrets.

**Solution**:
1. Verify secret names match exactly (case-sensitive)
2. Check that secrets are added at repository level or environment level
3. Ensure environment name in workflow matches environment in settings
4. Check workflow uses correct syntax: `${{ secrets.SECRET_NAME }}`

### Issue: Deployment Fails

**Problem**: Staging or production deployment step fails.

**Solution**:
1. Review the deployment scripts and customize for your platform
2. Ensure deployment secrets are correctly configured
3. Verify server/platform credentials are valid
4. Check network connectivity from GitHub Actions runners
5. Review logs in Actions tab for specific error messages

### Issue: Tests Don't Run

**Problem**: Test step shows "No tests directory found".

**Solution**:
1. Ensure `tests/` directory exists
2. Add test files following pytest naming convention (`test_*.py`)
3. Verify `pytest` is in `requirements-dev.txt`
4. Push changes and re-run workflow

### Issue: Can't Merge Even After Checks Pass

**Problem**: Merge button is disabled despite all checks passing.

**Solution**:
1. Check if all required reviews are provided
2. Verify all conversations are resolved
3. Ensure branch is up to date with main
4. Check if any required status checks are missing
5. Review branch protection rules for other requirements

### Issue: Workflow Takes Too Long

**Problem**: CI/CD pipeline is slow.

**Solution**:
1. Enable dependency caching (already configured)
2. Run tests in parallel (already configured with matrix)
3. Split integration tests to separate workflow if very slow
4. Consider using self-hosted runners for faster execution
5. Optimize test suite to remove slow tests

---

## Next Steps

After completing this setup:

1. ✅ Test the entire pipeline end-to-end
2. ✅ Document your deployment process in the scripts
3. ✅ Add your actual application code
4. ✅ Replace sample tests with real tests
5. ✅ Configure actual deployment targets
6. ✅ Set up monitoring and alerting
7. ✅ Train team members on the new workflow

## Additional Resources

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Environments Documentation](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)

## Support

If you encounter issues not covered here:
1. Check GitHub Actions logs for detailed error messages
2. Review the workflow YAML file syntax
3. Consult the GitHub Actions documentation
4. Create an issue in the repository
5. Reach out to your DevOps team

---

**Your CI/CD pipeline is now configured! 🎉**
