#!/bin/bash

# Test script to verify git operations work without running the full scraper
# This simulates the git portion of cron_scraper.sh

echo "=== Testing Git Operations ==="

# Change to the project directory
cd /home/conor/gitwork/epa_ireland_scraper

# Show current git status
echo "Current git status:"
git status --porcelain

# Test if we can access GitHub
echo ""
echo "Testing GitHub SSH connection..."
ssh -T git@github.com 2>&1 | head -1

# Get today's date for commit message
TODAY=$(date +%Y-%m-%d)
echo ""
echo "Today's date: $TODAY"

# Show what files would be added
echo ""
echo "Files that would be added to git:"
git add -A --dry-run

# Test commit (but don't actually commit anything new)
echo ""
echo "Testing git commit (dry run)..."
if git diff --cached --quiet && git diff --quiet; then
    echo "No changes to commit - this is expected for a test"
else
    echo "There are changes that would be committed:"
    git diff --name-only --cached
    git diff --name-only
fi

# Test git push access (but don't actually push)
echo ""
echo "Testing git push access..."
git ls-remote origin main > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Git push access verified - can reach GitHub"
else
    echo "❌ Git push access failed"
fi

echo ""
echo "=== Test Complete ==="
echo "If you want to actually test a commit/push, run:"
echo "  git add -A"
echo "  git commit -m 'Test commit - $(date)'"
echo "  git push origin main" 