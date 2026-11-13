#!/usr/bin/env bash
set -euo pipefail

source_dir=${1:-.}
site_dir=${2:?Indiquer le dossier de sortie du site}
mkdir -p "$site_dir"
cp -R "$source_dir/volumes_protocole" "$source_dir/annexes" "$site_dir/"
cp "$source_dir/index.html" "$source_dir/README.md" "$source_dir/llms.txt" "$site_dir/"
for name in LICENSE.md .nojekyll robots.txt sitemap.xml; do
  cp "$source_dir/fichiers_depot/$name" "$site_dir/$name"
done

# Les pages d’accès survivent aux changements de version.
while IFS=$'\t' read -r slug target; do
  if [[ ! "$slug" =~ ^ami-[a-z0-9]+(-[a-z0-9]+)*$ ||
        ! "$target" =~ ^(volumes_protocole|annexes)/[A-Za-z0-9_.-]+\.html$ ||
        ! -f "$site_dir/$target" ]]; then
    printf 'Route Pages invalide (%s → %s)\n' "$slug" "$target" >&2
    exit 1
  fi
done < "$source_dir/fichiers_depot/routes-webnode.tsv"

python3 "$source_dir/fichiers_depot/prepare_registre.py" "$source_dir" "$site_dir"

# Les montages Webnode suivent la même édition que les routes Pages.
python3 "$source_dir/fichiers_depot/webnode/build_webnode_assets.py" \
  --source "$source_dir" --site "$site_dir" \
  --templates "$source_dir/fichiers_depot/webnode/templates" \
  --annexes "$source_dir/fichiers_depot/webnode/routes-annexes.json" \
  --annex-template "$source_dir/fichiers_depot/webnode/annex.html" \
  --annex-shell "$source_dir/fichiers_depot/webnode/annex-shell.js" \
  --bootstrap "$source_dir/fichiers_depot/webnode/bootstrap.html"
