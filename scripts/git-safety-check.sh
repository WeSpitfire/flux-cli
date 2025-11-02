#!/bin/bash
# Git Safety Check - Prevents destructive operations on uncommitted work
# This should be run before any git checkout, reset, or clean operations

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛡️  Git Safety Check${NC}"
echo "================================"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo -e "${RED}❌ DANGER: You have uncommitted changes!${NC}"
    echo ""
    
    # Show what would be lost
    LINES_ADDED=$(git diff --numstat | awk '{added+=$1} END {print added}')
    LINES_DELETED=$(git diff --numstat | awk '{deleted+=$2} END {print deleted}')
    FILES_MODIFIED=$(git diff --name-only | wc -l | tr -d ' ')
    
    echo -e "${YELLOW}Changes that would be LOST:${NC}"
    echo "  • $FILES_MODIFIED files modified"
    echo "  • $LINES_ADDED lines added"
    echo "  • $LINES_DELETED lines deleted"
    echo ""
    
    # Show modified files
    echo -e "${YELLOW}Modified files:${NC}"
    git diff --name-only | sed 's/^/  • /'
    echo ""
    
    # Offer to stash
    echo -e "${GREEN}Would you like to:${NC}"
    echo "  1. Stash changes (recommended)"
    echo "  2. Create a backup commit"
    echo "  3. Cancel operation"
    echo "  4. Proceed anyway (DANGEROUS)"
    echo ""
    read -p "Enter choice (1-4): " choice
    
    case $choice in
        1)
            echo -e "${GREEN}📦 Stashing changes...${NC}"
            git stash push -m "Auto-stash before destructive operation at $(date)"
            echo -e "${GREEN}✅ Changes stashed! Run 'git stash pop' to restore.${NC}"
            ;;
        2)
            echo -e "${GREEN}💾 Creating backup commit...${NC}"
            git add -A
            git commit -m "WIP: Auto-backup before destructive operation at $(date)"
            echo -e "${GREEN}✅ Backup commit created!${NC}"
            ;;
        3)
            echo -e "${GREEN}✅ Operation cancelled.${NC}"
            exit 1
            ;;
        4)
            echo -e "${RED}⚠️  Proceeding without backup...${NC}"
            read -p "Type 'I understand the risk' to continue: " confirm
            if [ "$confirm" != "I understand the risk" ]; then
                echo -e "${RED}❌ Confirmation failed. Operation cancelled.${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}❌ Invalid choice. Operation cancelled.${NC}"
            exit 1
            ;;
    esac
else
    echo -e "${GREEN}✅ No uncommitted changes detected${NC}"
fi

# Check for untracked files
UNTRACKED=$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')
if [ "$UNTRACKED" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Warning: $UNTRACKED untracked files detected${NC}"
    git ls-files --others --exclude-standard | head -10 | sed 's/^/  • /'
    if [ "$UNTRACKED" -gt 10 ]; then
        echo "  ... and $((UNTRACKED - 10)) more"
    fi
    echo ""
fi

echo "================================"
echo -e "${GREEN}✅ Safety check complete${NC}"
