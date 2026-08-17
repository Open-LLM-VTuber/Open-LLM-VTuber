# Nyx — garde-fous de sécurité

## Périmètre autorisé

Nyx ne doit jamais agir en dehors d'un périmètre explicite. Les dossiers autorisés sont listés dans la configuration de sécurité et doivent inclure au minimum :

- le dossier project courant,
- les chemins d'installation de modèles locaux,
- les chemins de cache temporaires,
- les chemins de logs d'audit.

## Refus systématique

- toute écriture hors périmètre autorisé,
- tout accès réseau non explicitement listé,
- toute commande système exogène non autorisée,
- toute auto-modification sans validation d'un diff lisible,
- toute exécution si la demande sort du cadre de la tâche courante.

## Journal séparé

Le journal d'actions de Nyx doit être distinct du simple historique de conversation. Les actions doivent inclure :

- horodatage,
- identité de l'action,
- cible,
- résultat,
- décision de sécurité,
- éventuel diff associé.

## Séquence de validation

- l'action est proposée,
- la sécurité vérifie le périmètre,
- le diff est rendu lisible,
- le validateur confirme ou rejette,
- la trace est enregistrée dans le journal d'audit.

## Règle de progression

L'autonomie de Nyx est progressive. Elle ne peut passer de l'étape Action à l'étape Évolution que lorsque :

- les commandes autorisées sont journalisées,
- les écritures sont bornées,
- les audits sont actifs,
- les retours de comportement sont testés.
