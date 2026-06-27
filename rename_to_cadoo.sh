#!/usr/bin/env bash
# Rename cadoo → cadoo throughout the project (excludes venv, node_modules, __pycache__, .git)
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

echo "==> Working in: $REPO"

# ─── 1. Text substitutions in files ─────────────────────────────────────────

# Files to process (skip binary/generated/vendor dirs)
FILES=$(find . \
  -not \( -path "./venv/*" -prune \) \
  -not \( -path "./node_modules/*" -prune \) \
  -not \( -path "./.git/*" -prune \) \
  -not \( -path "./__pycache__/*" -prune \) \
  -not \( -path "./*.egg-info/*" -prune \) \
  -not \( -path "./uv.lock" -prune \) \
  -not \( -path "./package-lock.json" -prune \) \
  -type f \
  \( -name "*.py" -o -name "*.sh" -o -name "*.toml" -o -name "*.yaml" \
     -o -name "*.yml" -o -name "*.json" -o -name "*.md" -o -name "*.txt" \
     -o -name "*.rst" -o -name "*.cfg" -o -name "*.ini" -o -name "*.html" \
     -o -name "*.js" -o -name "*.ts" -o -name "*.css" -o -name "*.ps1" \
     -o -name "*.nix" -o -name "Dockerfile" -o -name "*.dockerfile" \)
)

echo "==> Replacing text in files..."
echo "$FILES" | while read -r f; do
  # Order matters: more-specific → less-specific
  sed -i \
    -e 's/cadoo/cadoo/g' \
    -e 's/cadoo/cadoo/g' \
    -e 's/CadooAgent/CadooAgent/g' \
    -e 's/CADOO_AGENT/CADOO_AGENT/g' \
    -e 's/cadoo_cli/cadoo_cli/g' \
    -e 's/CadooCLI/CadooCLI/g' \
    -e 's/CADOO_CLI/CADOO_CLI/g' \
    -e 's/cadoo_constants/cadoo_constants/g' \
    -e 's/cadoo_bootstrap/cadoo_bootstrap/g' \
    -e 's/cadoo_logging/cadoo_logging/g' \
    -e 's/cadoo_state/cadoo_state/g' \
    -e 's/cadoo_time/cadoo_time/g' \
    -e 's/CADOO_HOME/CADOO_HOME/g' \
    -e 's/cadoo_home/cadoo_home/g' \
    -e 's/\.cadoo/\.cadoo/g' \
    -e 's|/cadoo"|/cadoo"|g' \
    -e 's|doostudio/cadoo|doostudio/cadoo|g' \
    -e 's/DooStudio/DooStudio/g' \
    -e 's/DooStudio/DooStudio/g' \
    -e 's/setup-cadoo\.sh/setup-cadoo.sh/g' \
    -e 's/"cadoo"/"cadoo"/g' \
    -e "s/'cadoo'/'cadoo'/g" \
    -e 's/🟣 Cadoo/🟣 Cadoo/g' \
    -e 's/Cadoo Agent/Cadoo Agent/g' \
    -e 's/Cadoo CLI/Cadoo CLI/g' \
    -e 's/cadoo honcho/cadoo honcho/g' \
    -e 's/cadoo uninstall/cadoo uninstall/g' \
    -e 's/run `cadoo`/run `cadoo`/g' \
    -e 's/\bHermes\b/Cadoo/g' \
    -e 's/\bhermes\b/cadoo/g' \
    "$f" 2>/dev/null || true
done

echo "==> Text substitutions done."

# ─── 2. Rename directories ───────────────────────────────────────────────────
echo "==> Renaming directories..."

# cadoo_cli → cadoo_cli
if [ -d "./cadoo_cli" ]; then
  mv "./cadoo_cli" "./cadoo_cli"
  echo "    cadoo_cli → cadoo_cli"
fi

# cadoo → cadoo (top-level dir, not the whole repo)
if [ -d "./cadoo" ]; then
  mv "./cadoo" "./cadoo_core"
  echo "    cadoo/ → cadoo_core/"
fi

# egg-info
if [ -d "./cadoo.egg-info" ]; then
  mv "./cadoo.egg-info" "./cadoo.egg-info"
  echo "    cadoo.egg-info → cadoo.egg-info"
fi

echo "==> Directories renamed."

# ─── 3. Rename files ─────────────────────────────────────────────────────────
echo "==> Renaming files..."

find . \
  -not \( -path "./venv/*" -prune \) \
  -not \( -path "./node_modules/*" -prune \) \
  -not \( -path "./.git/*" -prune \) \
  -not \( -path "./__pycache__/*" -prune \) \
  -type f -name "*cadoo*" | sort -r | while read -r f; do
    new="${f//cadoo/cadoo}"
    dir=$(dirname "$new")
    mkdir -p "$dir"
    mv "$f" "$new"
    echo "    $(basename $f) → $(basename $new)"
done

echo "==> Files renamed."
echo ""
echo "==> Done! Project renamed to Cadoo."
