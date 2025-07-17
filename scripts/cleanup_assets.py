#!/usr/bin/env python3
"""
Asset Cleanup Script for ArXiv Weekly Popular

This script helps clean up irrelevant assets and prepare the repository
for independent use.
"""

import os
import shutil
from pathlib import Path
from typing import List

# Assets to remove (not relevant for the new system)
ASSETS_TO_REMOVE = [
    "assets/wechat_sponsor.JPG",
    "assets/use_docker.md", 
    "assets/fork.png",
    "assets/userid.png",
    "assets/subscribe_release.png",
    "assets/trigger.png"
]

# Assets to keep but should be updated
ASSETS_TO_UPDATE = [
    "assets/screenshot.png",  # Update with actual email output
    "assets/secrets.png",     # Update with your GitHub secrets interface
    "assets/repo_var.png",    # Update with your repository variables
    "assets/test.png"         # Update with your test workflow interface
]

# Assets that are fine to keep as-is
ASSETS_TO_KEEP = [
    "assets/logo.svg"
]

def main():
    """Clean up irrelevant assets and provide update guidance."""
    print("🧹 ArXiv Weekly Popular - Asset Cleanup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("assets").exists():
        print("❌ Error: 'assets' directory not found!")
        print("   Please run this script from the project root directory.")
        return
    
    # Remove irrelevant assets
    print("\n📁 Removing irrelevant assets...")
    removed_count = 0
    for asset_path in ASSETS_TO_REMOVE:
        if Path(asset_path).exists():
            try:
                Path(asset_path).unlink()
                print(f"   ✅ Removed: {asset_path}")
                removed_count += 1
            except Exception as e:
                print(f"   ❌ Failed to remove {asset_path}: {e}")
        else:
            print(f"   ℹ️  Not found: {asset_path}")
    
    print(f"\n📊 Removed {removed_count} irrelevant assets")
    
    # List assets that should be updated
    print("\n📝 Assets that should be updated:")
    for asset_path in ASSETS_TO_UPDATE:
        if Path(asset_path).exists():
            print(f"   ⚠️  Update needed: {asset_path}")
        else:
            print(f"   ❌ Missing: {asset_path}")
    
    # List assets that are fine to keep
    print("\n✅ Assets that are fine to keep:")
    for asset_path in ASSETS_TO_KEEP:
        if Path(asset_path).exists():
            print(f"   ✅ Keep: {asset_path}")
        else:
            print(f"   ❌ Missing: {asset_path}")
    
    # Provide next steps
    print("\n🎯 Next Steps:")
    print("1. Create new screenshots for the assets marked 'Update needed'")
    print("2. Test your GitHub Actions workflow")
    print("3. Take a screenshot of the email output")
    print("4. Update README.md badges with your repository information")
    print("\n📖 See SETUP_GUIDE.md for detailed instructions")
    
    print("\n✨ Cleanup complete!")

if __name__ == "__main__":
    main() 