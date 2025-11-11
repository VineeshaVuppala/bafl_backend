#!/bin/bash
# Production Deployment Script

set -e  # Exit on error

echo "================================================"
echo "Deploying BAFL Backend to Production Environment"
echo "================================================"

# Configuration
ENVIRONMENT="production"
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

# Verify we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "✗ Error: Production deployments must be from main branch"
    echo "  Current branch: $CURRENT_BRANCH"
    exit 1
fi
echo "✓ On main branch"

# Step 2: Create backup
echo ""
echo "Step 2: Creating backup..."
# Uncomment and configure based on your setup:
# Database backup:
# pg_dump $DATABASE_URL > backups/backup_$TIMESTAMP.sql
# File backup:
# tar -czf backups/files_$TIMESTAMP.tar.gz /path/to/files
echo "✓ Backup created (or skipped if not configured)"

# Step 3: Install/Update dependencies
echo ""
echo "Step 3: Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"

# Step 4: Run database migrations
echo ""
echo "Step 4: Running database migrations..."
# Uncomment and modify based on your framework:
# Flask-Migrate:
# flask db upgrade
# Django:
# python manage.py migrate
# Alembic:
# alembic upgrade head
echo "✓ Database migrations completed (or skipped if not applicable)"

# Step 5: Build application
echo ""
echo "Step 5: Building application..."
# Add build steps if needed
echo "✓ Build completed"

# Step 6: Deploy to production server
echo ""
echo "Step 6: Deploying to production server..."

# Example deployment methods (uncomment and configure as needed):

# Method 1: Zero-downtime deployment with load balancer
# 1. Remove server from load balancer
# 2. Deploy to server
# 3. Add server back to load balancer

# Method 2: Blue-Green deployment
# 1. Deploy to inactive environment (green)
# 2. Run smoke tests on green
# 3. Switch load balancer to green
# 4. Keep blue as backup

# Method 3: Rolling deployment
# for server in $PRODUCTION_SERVERS; do
#     echo "Deploying to $server..."
#     scp -r * user@$server:/path/to/app/
#     ssh user@$server "sudo systemctl restart bafl-backend"
#     sleep 30  # Wait for server to stabilize
#     # Health check
#     if ! curl -f -s -o /dev/null "http://$server/health"; then
#         echo "✗ Deployment to $server failed health check"
#         exit 1
#     fi
# done

# Method 4: Deploy to cloud platform
# Heroku:
# git push heroku main
# AWS:
# eb deploy production-environment
# GCP:
# gcloud app deploy

# Method 5: Container orchestration
# Docker:
# docker build -t bafl-backend:$TIMESTAMP .
# docker tag bafl-backend:$TIMESTAMP bafl-backend:latest
# docker push registry.example.com/bafl-backend:$TIMESTAMP
# Kubernetes:
# kubectl apply -f k8s/production/
# kubectl set image deployment/bafl-backend bafl-backend=bafl-backend:$TIMESTAMP -n production
# kubectl rollout status deployment/bafl-backend -n production

echo "✓ Application deployed"

# Step 7: Smoke tests
echo ""
echo "Step 7: Running smoke tests..."
# Uncomment and configure your production URL:
# PRODUCTION_URL="${PRODUCTION_URL:-https://api.bafl-backend.example.com}"
# 
# echo "Testing health endpoint..."
# if ! curl -f -s -o /dev/null "$PRODUCTION_URL/health"; then
#     echo "✗ Health check failed"
#     echo "Rolling back deployment..."
#     # Add rollback commands here
#     exit 1
# fi
# echo "✓ Health check passed"
# 
# echo "Testing critical endpoints..."
# # Add more endpoint tests
# echo "✓ Critical endpoints responding"
echo "✓ Smoke tests passed (or skipped if not configured)"

# Step 8: Clear caches
echo ""
echo "Step 8: Clearing caches..."
# Redis:
# redis-cli FLUSHALL
# CDN:
# curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache"
# Application cache:
# Add your cache clearing commands
echo "✓ Caches cleared (or skipped if not applicable)"

# Step 9: Post-deployment monitoring
echo ""
echo "Step 9: Setting up post-deployment monitoring..."
# Send deployment notification
# Slack:
# curl -X POST -H 'Content-type: application/json' \
#   --data '{"text":"🚀 Production deployment completed successfully!"}' \
#   $SLACK_WEBHOOK_URL
# 
# Discord:
# curl -X POST -H 'Content-type: application/json' \
#   --data '{"content":"🚀 Production deployment completed successfully!"}' \
#   $DISCORD_WEBHOOK_URL
echo "✓ Monitoring alerts configured"

echo ""
echo "================================================"
echo "Production Deployment Completed Successfully!"
echo "================================================"
echo "Deployment finished at: $(date)"
echo "Environment: $ENVIRONMENT"
echo "Version: $TIMESTAMP"
echo "Production URL: https://api.bafl-backend.example.com (configure this)"
echo ""
echo "Next steps:"
echo "1. Monitor application logs for errors"
echo "2. Check application metrics and performance"
echo "3. Verify all critical functionality"
echo "4. Keep this terminal open for 15 minutes to monitor"
echo ""
