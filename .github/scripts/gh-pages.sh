#!/usr/bin/env bash
# Publish or remove one branch's documentation on the gh-pages branch, which
# GitHub Pages serves as https://heman.github.io/binmap/<branch>/.
#
#   gh-pages.sh publish <branch> <built-site-directory>
#   gh-pages.sh remove  <branch>
#
# Each branch gets its own folder; branch names containing "/" become nested
# folders. The root index.html lists every published branch, found by the
# objects.inv file Sphinx writes at the top of each site. Run it from a clone of
# the repository; REMOTE (default "origin") is the remote to push to.
set -euo pipefail

usage() {
    echo "usage: $0 publish <branch> <site-directory> | remove <branch>" >&2
    exit 2
}

action=${1:-}
branch=${2:-}
site=${3:-}
remote=${REMOTE:-origin}

case "$action" in
    publish) [[ -n "$branch" && -d "$site" ]] || usage ;;
    remove) [[ -n "$branch" ]] || usage ;;
    *) usage ;;
esac
if [[ "$branch" == "index.html" || "$branch" == .* ]]; then
    echo "Refusing branch name '$branch': it collides with the gh-pages root" >&2
    exit 1
fi

workdir=$(mktemp -d)
cleanup() {
    git worktree remove --force "$workdir" >/dev/null 2>&1 || true
    rm -rf "$workdir"
}
trap cleanup EXIT

if git fetch --quiet "$remote" gh-pages 2>/dev/null; then
    git worktree add --quiet --detach "$workdir" FETCH_HEAD
else
    # First publish: gh-pages doesn't exist yet, so start an unrelated history.
    git worktree add --quiet --detach "$workdir"
    git -C "$workdir" switch --quiet --orphan gh-pages
fi

target="$workdir/$branch"
rm -rf "$target"
if [[ "$action" == publish ]]; then
    mkdir -p "$target"
    cp -R "$site"/. "$target"/
fi
# Remove folders left empty, e.g. "feature/" after removing "feature/x".
find "$workdir" -mindepth 1 -type d -empty -not -path "$workdir/.git/*" -delete

# Sphinx puts its assets in _static/; without this, GitHub Pages' Jekyll step
# would drop every folder starting with an underscore.
touch "$workdir/.nojekyll"

python3 - "$workdir" <<'EOF'
import html
import os
import sys
import urllib.parse

root = sys.argv[1]
branches = sorted(
    os.path.relpath(dirpath, root)
    for dirpath, dirnames, filenames in os.walk(root)
    if ".git" not in os.path.relpath(dirpath, root).split(os.sep)
    and dirpath != root
    and "objects.inv" in filenames
)
# master first, then the other branches alphabetically
branches.sort(key=lambda name: name != "master")
items = "\n".join(
    f'    <li><a href="{html.escape(urllib.parse.quote(name))}/">{html.escape(name)}</a></li>'
    for name in branches
)
with open(os.path.join(root, "index.html"), "w", encoding="utf-8") as index:
    index.write(f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>binmap documentation by branch</title>
</head>
<body>
  <h1>binmap documentation by branch</h1>
  <p>Released versions: <a href="https://binmap.readthedocs.io/">binmap.readthedocs.io</a></p>
  <ul>
{items}
  </ul>
</body>
</html>
""")
EOF

git -C "$workdir" add --all
if git -C "$workdir" diff --cached --quiet; then
    echo "gh-pages already up to date for $branch"
    exit 0
fi
git -C "$workdir" \
    -c user.name="github-actions[bot]" \
    -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
    commit --quiet -m "Docs: $action $branch"
git -C "$workdir" push --quiet "$remote" HEAD:refs/heads/gh-pages
if [[ "$action" == publish ]]; then
    echo "gh-pages: published $branch"
else
    echo "gh-pages: removed $branch"
fi
