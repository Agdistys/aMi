# Fichiers du dépôt aMi

Le dépôt contient les HTML et leurs versions texte. L’Index du Protocole est l’accueil. Le fichier `index.html` à la racine y mène.

- `volumes_protocole/` contient l’Index et les volumes.
- `annexes/` contient les annexes, la page MétaMatrice et son classeur public.
- `fichiers_depot/` contient les fichiers techniques. `assemble-pages.sh` rassemble les éléments nécessaires dans la sortie destinée à Pages.

`README.md` et `llms.txt` restent à la racine avec l’entrée du site pour être trouvés directement. GitHub lit le workflow dans `.github/workflows/`. Quand le dépôt existe et que Pages utilise GitHub Actions, ce workflow publie les modifications de la branche `main`.

`CNAME` consigne le domaine prévu. Avec GitHub Actions, le domaine se règle dans **Settings → Pages → Custom domain**. Le DNS de `ami.agdistys.fr` doit ensuite pointer par CNAME vers `agdistys.github.io`.

Une pré-release correspond à un commit précis. Pages sert le HTML de la branche publiée à une adresse stable. Un ZIP de l’édition peut être proposé comme téléchargement de la pré-release.

## Bloc Webnode commun

`webnode/bootstrap.html` est le bloc HTML à coller une seule fois dans chaque page Webnode du Protocole. Le même code choisit le volume ou l’annexe selon l’adresse de la page. Le sommaire des annexes affiche des liens. Les pages d’annexe affichent leur édition GitHub Pages dans la page Webnode, avec un seul défilement.

Pour publier une nouvelle édition, ajouter le fichier charté et mettre à jour sa cible dans `routes-webnode.tsv`. Pour l’Index, mettre à jour le renvoi de `index.html`. Le déploiement recalcule le catalogue et les empreintes des fichiers. Les corrections d’affichage propres à Webnode se font dans `webnode/templates/`. Si une nouvelle édition change la racine HTML attendue, adapter son modèle au cours de la même mise à jour. Les anciennes éditions restent accessibles à leurs adresses.

Le bloc récupère le catalogue à chaque chargement depuis GitHub Pages. Le navigateur vérifie l’intégrité de l’intégrateur, puis l’intégrateur vérifie le volume. Le catalogue et ses empreintes sont servis par le même dépôt. Le catalogue ne couvre que l’Index, les 25 volumes et les annexes publiques déclarées.
