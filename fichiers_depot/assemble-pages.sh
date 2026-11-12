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
