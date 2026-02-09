#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# SortMeOut — Build macOS .app and .dmg installer
#
# Usage:  ./build_app.sh
# Output: dist/SortMeOut.app and dist/SortMeOut-Installer.dmg
# ═══════════════════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "═══════════════════════════════════════════════════════════"
echo "  SortMeOut — Building macOS Application"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ── Check venv ──
if [ ! -f ".venv/bin/python" ]; then
    echo "❌ Virtual environment not found. Run: python -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

PYTHON=".venv/bin/python"
PIP=".venv/bin/pip"

# ── Ensure PyInstaller is installed ──
if ! $PYTHON -m PyInstaller --version &>/dev/null; then
    echo "📦 Installing PyInstaller..."
    $PIP install pyinstaller
fi

# ── Generate icon if missing ──
if [ ! -f "sortmeout/resources/SortMeOut.icns" ]; then
    echo "🎨 Generating app icon..."
    $PYTHON generate_icon.py
fi

# ── Clean previous build ──
echo "🧹 Cleaning previous build..."
rm -rf build/SortMeOut dist/SortMeOut dist/SortMeOut.app

# ── Build .app ──
echo "🔨 Building SortMeOut.app..."
$PYTHON -m PyInstaller SortMeOutDesktop.spec --clean --noconfirm

# ── Verify ──
if [ ! -d "dist/SortMeOut.app" ]; then
    echo "❌ Build failed — dist/SortMeOut.app not found"
    exit 1
fi

APP_SIZE=$(du -sh "dist/SortMeOut.app" | cut -f1)
echo "✅ SortMeOut.app built successfully ($APP_SIZE)"
echo ""

# ── Create DMG ──
echo "📀 Creating DMG installer..."

DMG_NAME="SortMeOut-Installer"
DMG_PATH="dist/${DMG_NAME}.dmg"
DMG_TMP="dist/${DMG_NAME}-tmp.dmg"
DMG_STAGING="dist/dmg-staging"

# Clean staging
rm -rf "$DMG_STAGING" "$DMG_PATH" "$DMG_TMP"
mkdir -p "$DMG_STAGING"

# Copy app to staging
cp -R "dist/SortMeOut.app" "$DMG_STAGING/"

# Create Applications symlink
ln -s /Applications "$DMG_STAGING/Applications"

# Create background instructions
cat > "$DMG_STAGING/.background_install.txt" << 'EOF'
Drag SortMeOut to Applications to install.
EOF

# Create temporary DMG
hdiutil create -volname "SortMeOut" \
    -srcfolder "$DMG_STAGING" \
    -ov -format UDRW \
    "$DMG_TMP"

# Convert to compressed read-only DMG
hdiutil convert "$DMG_TMP" -format UDZO -o "$DMG_PATH"
rm -f "$DMG_TMP"
rm -rf "$DMG_STAGING"

DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
echo "✅ ${DMG_NAME}.dmg created ($DMG_SIZE)"
echo ""

echo "═══════════════════════════════════════════════════════════"
echo "  ✅ BUILD COMPLETE"
echo ""
echo "  App:       dist/SortMeOut.app"
echo "  Installer: dist/${DMG_NAME}.dmg"
echo ""
echo "  To install: Open the DMG and drag SortMeOut to Applications"
echo "  To run:     Double-click SortMeOut.app"
echo "═══════════════════════════════════════════════════════════"
