#!/bin/sh
# Exit 1 when product files changed and verify.json is missing or older than those files.
set -eu

root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$root" ]; then
  exit 0
fi
cd "$root"

changes=$(git status --porcelain -u -- . ":(exclude).spec" ":(exclude).cursor" ":(exclude)AGENTS.md" ":(exclude)CLAUDE.md" || true)
if [ -z "$changes" ]; then
  exit 0
fi

newest=0
stamp=""
if [ -d .spec/tasks ]; then
  list=$(mktemp)
  find .spec/tasks -name verify.json -type f > "$list" 2>/dev/null || true
  while IFS= read -r file; do
    [ -n "$file" ] || continue
    m=$(stat -f %m "$file" 2>/dev/null || stat -c %Y "$file")
    if [ "$m" -gt "$newest" ]; then
      newest=$m
      stamp=$file
    fi
  done < "$list"
  rm -f "$list"
fi

if [ -z "$stamp" ]; then
  echo "Product files changed and .spec/tasks/<id>/verify.json is missing." >&2
  exit 1
fi

product_m=0
oldifs=$IFS
IFS='
'
for line in $changes; do
  [ -n "$line" ] || continue
  file=$(printf '%s' "$line" | cut -c4-)
  case "$file" in
    *" -> "*) file=${file##* -> } ;;
  esac
  file=$(printf '%s' "$file" | tr -d '"')
  if [ -e "$file" ]; then
    fm=$(stat -f %m "$file" 2>/dev/null || stat -c %Y "$file")
    if [ "$fm" -gt "$product_m" ]; then
      product_m=$fm
    fi
  fi
done
IFS=$oldifs

if [ "$product_m" -gt "$newest" ]; then
  echo "verify.json is older than a changed product file. Run the Verify commands and rewrite the stamp." >&2
  exit 1
fi

exit 0
