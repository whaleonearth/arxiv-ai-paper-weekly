#!/usr/bin/env python3
"""
README Badge Update Script for ArXiv Weekly Popular

This script helps update the README badges with your actual repository information.
"""

import re
from pathlib import Path

def update_readme_badges(username: str, repo_name: str):
    """Update README badges with actual repository information."""
    
    readme_path = Path("README.md")
    if not readme_path.exists():
        print("❌ README.md not found!")
        return False
    
    # Read the current README
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define the replacements
    replacements = [
        (r'YOUR_USERNAME/YOUR_REPO_NAME', f'{username}/{repo_name}'),
        (r'YOUR_USERNAME', username),
        (r'YOUR_REPO_NAME', repo_name),
    ]
    
    # Apply replacements
    updated_content = content
    changes_made = 0
    
    for old_pattern, new_value in replacements:
        new_content = re.sub(old_pattern, new_value, updated_content)
        if new_content != updated_content:
            changes_made += len(re.findall(old_pattern, updated_content))
            updated_content = new_content
    
    # Write back the updated content
    if changes_made > 0:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"✅ Updated {changes_made} references in README.md")
        print(f"   Repository: {username}/{repo_name}")
        return True
    else:
        print("ℹ️  No placeholders found to update")
        return False

def main():
    """Main function to update README badges."""
    print("📝 ArXiv Weekly Popular - README Badge Updater")
    print("=" * 50)
    
    # Get repository information
    username = input("Enter your GitHub username: ").strip()
    repo_name = input("Enter your repository name: ").strip()
    
    if not username or not repo_name:
        print("❌ Username and repository name are required!")
        return
    
    # Validate input
    if not re.match(r'^[a-zA-Z0-9\-_]+$', username):
        print("❌ Invalid username format!")
        return
    
    if not re.match(r'^[a-zA-Z0-9\-_\.]+$', repo_name):
        print("❌ Invalid repository name format!")
        return
    
    print(f"\n🔄 Updating badges for: {username}/{repo_name}")
    
    # Update the badges
    success = update_readme_badges(username, repo_name)
    
    if success:
        print("\n✅ Badge update complete!")
        print(f"   Your repository: https://github.com/{username}/{repo_name}")
        print("\n🎯 Next steps:")
        print("1. Commit and push the updated README.md")
        print("2. Check that the badges display correctly on GitHub")
        print("3. Configure GitHub Actions secrets and variables")
        print("4. Test your workflow!")
    else:
        print("\n⚠️  No changes were made to README.md")

if __name__ == "__main__":
    main() 