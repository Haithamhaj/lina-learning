#!/usr/bin/env bash
# Build the bounded Reserved-VM artifact without retaining build caches.
set -euo pipefail

repository_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "build must run from a Git checkout" >&2
  exit 1
}

if [[ "$(pwd -P)" != "$(cd "$repository_root" && pwd -P)" ]]; then
  echo "build must run from the repository root: $repository_root" >&2
  exit 1
fi

standalone_dir="apps/web/.next/standalone"
standalone_staging_dir=".replit-next-standalone"
npm_cache_dir=".cache/npm"
uv_cache_dir=".cache/uv"
build_temp_dir=".replit-build-tmp"

# Only generated environments, package trees, and build caches are removed.
rm -rf -- ".venv-production" "apps/web/.next" "node_modules" "$npm_cache_dir" "$uv_cache_dir" "$standalone_staging_dir" "$build_temp_dir"
trap 'rm -rf -- "$build_temp_dir"' EXIT

# Build Next while the production Python environment does not occupy the quota.
export NPM_CONFIG_CACHE="$npm_cache_dir"
npm ci --include=dev
if [[ -n "${CLERK_PUBLISHABLE_KEY:-}" ]]; then
  export NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="$CLERK_PUBLISHABLE_KEY"
fi
npm --prefix apps/web run build

test -f "$standalone_dir/apps/web/server.js"
mkdir -p "$standalone_dir/apps/web/.next"
cp -R "apps/web/.next/static" "$standalone_dir/apps/web/.next/static"
if [[ -d "apps/web/public" ]]; then
  cp -R "apps/web/public" "$standalone_dir/apps/web/public"
fi

# Keep only the runnable Next artifact before materializing the large Python runtime.
mv "$standalone_dir" "$standalone_staging_dir"
rm -rf -- "apps/web/.next" "node_modules" "$npm_cache_dir"
mkdir -p "apps/web/.next"
mv "$standalone_staging_dir" "$standalone_dir"
test -f "$standalone_dir/apps/web/server.js"
test ! -d "node_modules"

export UV_NO_CACHE=1
mkdir -p "$build_temp_dir"
export TMPDIR="$build_temp_dir"
uv venv --clear ".venv-production"
uv pip install --python ".venv-production/bin/python" --index-url https://download.pytorch.org/whl/cpu --constraint "apps/api/production-constraints.txt" torch torchvision
uv pip install --python ".venv-production/bin/python" --constraint "apps/api/production-constraints.txt" --requirements "apps/api/requirements.txt"
".venv-production/bin/python" -m scripts.validate_production_runtime

test -f "$standalone_dir/apps/web/server.js"
test ! -d "node_modules"
