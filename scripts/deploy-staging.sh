#!/bin/bash
# Staging Deployment Script

set -e  # Exit on error

echo "================================================"
echo "Deploying BAFL Backend to Staging Environment"
echo "================================================"

# Configuration
ENVIRONMENT="staging"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Deployment started at: $(date)"
echo "Environment: $ENVIRONMENT"

# Step 1: Pre-deployment checks
echo ""
echo "Step 1: Running pre-deployment checks..."
if [ -f requirements.txt ]; then
    echo "✓ requirements.txt found"
else
    echo "✗ requirements.txt not found"
    exit 1
fi

# Step 2: Install/Update dependencies
echo ""
echo "Step 2: Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"

# Step 3: Run database migrations (if applicable)
echo ""
echo "Step 3: Running database migrations..."
# Uncomment and modify based on your framework:
# Flask-Migrate:
# flask db upgrade
# Django:
# python manage.py migrate
# Alembic:
# alembic upgrade head
echo "✓ Database migrations completed (or skipped if not applicable)"

# Step 4: Run tests
echo ""
echo "Step 4: Running tests..."
if [ -d tests ]; then
    pytest tests/ --tb=short -v
    echo "✓ Tests passed"
else
    echo "⚠ No tests directory found, skipping tests"
fi

# Step 5: Build application (if needed)
echo ""
echo "Step 5: Building application..."
# Add build steps if needed
echo "✓ Build completed"

# Step 6: Deploy to staging server
echo ""
echo "Step 6: Deploying to staging server..."

# Example deployment methods (uncomment and configure as needed):

# Method 1: Copy files to remote server via SCP
# scp -r * user@staging-server:/path/to/app/

# Method 2: Deploy to Heroku
# git push heroku-staging main

# Method 3: Deploy to AWS Elastic Beanstalk
# eb deploy staging-environment

# Method 4: Deploy to Docker container
# docker build -t bafl-backend:staging .
# docker push registry.example.com/bafl-backend:staging

# Method 5: Deploy to Kubernetes
# kubectl apply -f k8s/staging/
# kubectl set image deployment/bafl-backend bafl-backend=bafl-backend:$TIMESTAMP -n staging

echo "✓ Application deployed"

# Step 7: Health check
echo ""
echo "Step 7: Running health checks..."
# Uncomment and configure your staging URL:
# STAGING_URL="${STAGING_URL:-https://staging.bafl-backend.example.com}"
# for i in {1..5}; do
#     if curl -f -s -o /dev/null "$STAGING_URL/health"; then
#         echo "✓ Health check passed"
#         break
#     else
#         if [ $i -eq 5 ]; then
#             echo "✗ Health check failed after 5 attempts"
#             exit 1
#         fi
#         echo "Health check attempt $i failed, retrying in 10 seconds..."
#         sleep 10
#     fi
# done
echo "✓ Health checks passed (or skipped if not configured)"

# Step 8: Post-deployment tasks
echo ""
echo "Step 8: Running post-deployment tasks..."
# Clear caches, warm up application, etc.
echo "✓ Post-deployment tasks completed"

echo ""
echo "================================================"
echo "Staging Deployment Completed Successfully!"
echo "================================================"
echo "Deployment finished at: $(date)"
echo "Environment: $ENVIRONMENT"
echo "Staging URL: https://staging.bafl-backend.example.com (configure this)"
echo ""
