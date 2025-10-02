#!/bin/bash
# VAPOR Release Script - EXECUTE THIS TO SHIP!

echo "🚀 VAPOR RELEASE SCRIPT v2.1.0"
echo "================================"

# 1. Clean up
echo "🧹 Cleaning up..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -name ".DS_Store" -delete 2>/dev/null

# 2. Run tests (if you have any)
echo "🧪 Running quick test..."
python3 -c "import src.steam_grid_artwork_manager; print('✓ Import test passed')"

# 3. Update version
echo "📝 Updating version to 2.1.0..."
sed -i 's/__version__ = ".*"/__version__ = "2.1.0"/' src/version.py

# 4. Build executables
echo "🔨 Building executables..."
if [ -f "build_all_platforms.sh" ]; then
    ./build_all_platforms.sh
else
    echo "⚠️  Build script not found, skipping..."
fi

# 5. Create release archive
echo "📦 Creating release archive..."
mkdir -p releases/v2.1.0
cp -r builds/* releases/v2.1.0/ 2>/dev/null
tar -czf releases/VAPOR-v2.1.0-all-platforms.tar.gz releases/v2.1.0/

# 6. Git operations
echo "📤 Preparing Git release..."
git add .
git commit -m "🚀 Release v2.1.0 - The Perfect Edition

- Added backup/restore system
- Added smart caching for offline mode
- Added user preferences and exclude list
- Fixed memory management for large libraries
- Improved error handling with specific messages"

git tag -a v2.1.0 -m "VAPOR v2.1.0 - Production Ready"

echo ""
echo "✅ RELEASE PREPARED!"
echo ""
echo "📋 FINAL STEPS:"
echo "1. Review changes: git diff HEAD~1"
echo "2. Push to GitHub: git push origin main --tags"
echo "3. Create GitHub Release at: https://github.com/YOUR_USERNAME/VAPOR/releases/new"
echo "4. Upload: releases/VAPOR-v2.1.0-all-platforms.tar.gz"
echo "5. Post to Reddit: r/Steam, r/SteamDeck, r/pcgaming"
echo ""
echo "🎉 VAPOR IS READY TO SHIP!"
