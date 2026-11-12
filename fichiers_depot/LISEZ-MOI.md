# Fichiers du dépôt aMi

Le dépôt contient les HTML et leurs versions texte. L’Index du Protocole est l’accueil. Le fichier `index.html` à la racine y mène.

- `volumes_protocole/` contient l’Index et les volumes.
- `annexes/` contient les annexes, la page MétaMatrice et son classeur public.
- `fichiers_depot/` contient les fichiers techniques. `assemble-pages.sh` rassemble les éléments nécessaires dans la sortie destinée à Pages.

`README.md` et `llms.txt` restent à la racine avec l’entrée du site pour être trouvés directement. GitHub lit le workflow dans `.github/workflows/`. Quand le dépôt existe et que Pages utilise GitHub Actions, ce workflow publie les modifications de la branche `main`.

`CNAME` consigne le domaine prévu. Avec GitHub Actions, le domaine se règle dans **Settings → Pages → Custom domain**. Le DNS de `ami.agdistys.fr` doit ensuite pointer par CNAME vers `agdistys.github.io`.

Une pré-release correspond à un commit précis. Pages sert le HTML de la branche publiée à une adresse stable. Un ZIP de l’édition peut être proposé comme téléchargement de la pré-release.
