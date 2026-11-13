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

# Les blocs Webnode ouvrent un alias qui survit aux changements de version.
while IFS=$'\t' read -r slug target; do
  if [[ ! "$slug" =~ ^ami-[a-z0-9]+(-[a-z0-9]+)*$ ||
        ! "$target" =~ ^(volumes_protocole|annexes)/[A-Za-z0-9_.-]+\.html$ ||
        ! -f "$site_dir/$target" ]]; then
    printf 'Route Pages invalide (%s → %s)\n' "$slug" "$target" >&2
    exit 1
  fi
  mkdir "$site_dir/$slug"
  cat > "$site_dir/$slug/index.html" <<HTML
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,follow">
  <link rel="canonical" href="../$target">
  <title>Ouvrir le volume aMi</title>
</head>
<body>
  <p><a id="volume" href="../$target">Ouvrir la page du Protocole aMi</a></p>
  <script>
    const volume = document.getElementById('volume');
    volume.href += location.search + location.hash;
    location.replace(volume.href);
  </script>
</body>
</html>
HTML
done < "$source_dir/fichiers_depot/routes-webnode.tsv"

# Les montages Webnode suivent la même édition que les routes Pages.
python3 "$source_dir/fichiers_depot/webnode/build_webnode_assets.py" \
  --source "$source_dir" --site "$site_dir" \
  --templates "$source_dir/fichiers_depot/webnode/templates" \
  --annexes "$source_dir/fichiers_depot/webnode/routes-annexes.json" \
  --annex-template "$source_dir/fichiers_depot/webnode/annex.html" \
  --annex-shell "$source_dir/fichiers_depot/webnode/annex-shell.js" \
  --bootstrap "$source_dir/fichiers_depot/webnode/bootstrap.html"
