#!/usr/bin/env python3
"""
Test script for Git operations
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.git_tool import (
    git_status, 
    git_diff, 
    git_branch_list, 
    git_log,
    git_commit,
    git_create_branch
)

def test_git_operations():
    """Test all Git operations"""
    print("🧪 Testing Git Operations...\n")
    
    # Test 1: Git Status
    print("1. 📊 Git Status:")
    print("-" * 60)
    result = git_status()
    if result["success"]:
        if result["has_changes"]:
            print(f"Changes detected:\n{result['status']}")
        else:
            print("✅ No changes")
    else:
        print(f"❌ Error: {result['error']}")
    
    # Test 2: Git Branches
    print("\n2. 🌳 Git Branches:")
    print("-" * 60)
    result = git_branch_list()
    if result["success"]:
        print(f"Current branch: {result['current']}")
        print(f"All branches ({len(result['branches'])}):")
        for branch in result['branches'][:5]:  # Show first 5
            print(f"  {branch}")
    else:
        print(f"❌ Error: {result['error']}")
    
    # Test 3: Git Log
    print("\n3. 📜 Git Log (last 5 commits):")
    print("-" * 60)
    result = git_log(5)
    if result["success"]:
        for commit in result['commits']:
            print(f"  {commit}")
    else:
        print(f"❌ Error: {result['error']}")
    
    # Test 4: Git Diff
    print("\n4. 🔍 Git Diff:")
    print("-" * 60)
    result = git_diff()
    if result["success"]:
        if result['diff']:
            print(result['diff'][:500])  # Show first 500 chars
            if len(result['diff']) > 500:
                print("... (truncated)")
        else:
            print("✅ No unstaged changes")
    else:
        print(f"❌ Error: {result['error']}")
    
    print("\n" + "=" * 60)
    print("✅ Git operations test complete!")
    print("\n💡 To test commit/branch creation, use:")
    print("   - git_commit('test commit')")
    print("   - git_create_branch('test-branch')")

if __name__ == "__main__":
    test_git_operations()
