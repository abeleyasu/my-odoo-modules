#!/bin/bash
# Script to push RingCentral pricing updates to all version branches
# Run this script to complete the manual push steps for branches 16.0, 17.0, and 19.0

set -e  # Exit on error

echo "================================================"
echo "RingCentral Pricing Update - Branch Push Script"
echo "================================================"
echo ""

# Check if we're in the right directory
if [ ! -d "ringcentral_suite" ]; then
    echo "ERROR: This script must be run from the repository root directory"
    exit 1
fi

# Function to push a branch
push_branch() {
    local branch=$1
    local version=$2
    
    echo "Processing branch: $branch (Odoo $version)"
    echo "----------------------------------------"
    
    # Check if branch exists
    if git show-ref --verify --quiet refs/heads/$branch; then
        echo "✓ Branch $branch exists locally"
        
        # Checkout the branch
        git checkout $branch
        
        # Show the changes
        echo ""
        echo "Files modified in this branch:"
        git diff --name-only $version | grep __manifest__.py || echo "  (All manifest files)"
        echo ""
        
        # Push to origin
        echo "Pushing $branch to origin..."
        if git push origin $branch; then
            echo "✅ Successfully pushed $branch"
        else
            echo "❌ Failed to push $branch"
            echo "   You may need to authenticate or create a PR manually"
        fi
    else
        echo "⚠️  Branch $branch not found locally"
        echo "   The changes may have already been pushed or the branch was not created"
    fi
    echo ""
}

# Push each version branch
echo "Starting push process for all version branches..."
echo ""

push_branch "copilot/update-ringcentral-pricing-16.0" "16.0"
push_branch "copilot/update-ringcentral-pricing-17.0" "17.0"
push_branch "copilot/update-ringcentral-pricing-19.0" "19.0"

# Return to the original copilot branch
echo "Returning to main copilot branch..."
git checkout copilot/update-ringcentral-module-pricing

echo ""
echo "================================================"
echo "Push process complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Create pull requests for each branch:"
echo "   - copilot/update-ringcentral-pricing-16.0 → 16.0"
echo "   - copilot/update-ringcentral-pricing-17.0 → 17.0"
echo "   - copilot/update-ringcentral-pricing-19.0 → 19.0"
echo ""
echo "2. Review and merge each PR"
echo ""
echo "3. The main copilot branch (18.0) is already pushed and ready for merge"
echo ""
echo "For more details, see: RINGCENTRAL_PRICING_UPDATE_SUMMARY.md"
