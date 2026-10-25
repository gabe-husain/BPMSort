#!/bin/bash
# Builds "Spoti-Viz.app", a tiny floating always-on-top widget of the /player page.
# Native Swift, logs in to Spotify itself using PKCE (no client secret, no server).
#   widget/build.sh            build into widget/build/
#   widget/build.sh --install  also copy it to ~/Applications
set -euo pipefail

WIDGET_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$WIDGET_DIR")"
APP="$WIDGET_DIR/build/Spoti-Viz.app"

# Client ID comes from the repo's .env, falls back to the BPMSort app's public client ID
CLIENT_ID="${CLIENT_ID:-$(grep -s '^CLIENT_ID' "$REPO/.env" | cut -d= -f2- | tr -d ' "'\''' || true)}"
CLIENT_ID="${CLIENT_ID:-b0974a4308d2409ba90a3694febda89f}"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
swiftc -Osize "$WIDGET_DIR/PlayerWidget.swift" -o "$APP/Contents/MacOS/SpotiViz"
strip -x "$APP/Contents/MacOS/SpotiViz"

ICONSET="$WIDGET_DIR/build/AppIcon.iconset"
swift "$WIDGET_DIR/make_icon.swift" "$ICONSET"
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/AppIcon.icns"
rm -rf "$ICONSET"
cp "$WIDGET_DIR/vinyl.svg" "$APP/Contents/Resources/vinyl.svg"

cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>Spoti-Viz</string>
    <key>CFBundleIdentifier</key><string>com.gabehusain.spotiviz</string>
    <key>CFBundleIconFile</key><string>AppIcon</string>
    <key>CFBundleExecutable</key><string>SpotiViz</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>LSMinimumSystemVersion</key><string>13.0</string>
    <key>LSUIElement</key><true/>
    <key>SpotifyClientID</key><string>$CLIENT_ID</string>
</dict>
</plist>
EOF

codesign --force -s - "$APP" >/dev/null 2>&1
echo "Built $APP ($(du -sh "$APP" | cut -f1))"

if [ "${1:-}" = "--install" ]; then
    mkdir -p "$HOME/Applications"
    rm -rf "$HOME/Applications/Spoti-Viz.app"
    cp -R "$APP" "$HOME/Applications/"
    echo "Installed to ~/Applications/Spoti-Viz.app"
fi

echo "Spotify Dashboard needs this Redirect URI: http://127.0.0.1:47823/callback"
