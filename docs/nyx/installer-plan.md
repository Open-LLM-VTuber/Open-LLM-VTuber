# Nyx — plan d'installateur Windows

## Objectif

Produire un unique exécutable `.exe` qui installe le backend local, les dépendances, Open-LLM-VTuber, les modèles et la configuration Nyx sans étape manuelle.

## Étapes

1. Bundle du runtime Python avec PyInstaller.
   - Installer la dépendance de packaging avec `uv sync --extra packaging` ou `uv pip install -e ".[packaging]"`.
2. Packaging du backend local et des ressources statiques.
3. Inclusion des modules ASR/TTS/Live2D.
4. Déploiement des modèles locaux dans un dossier dédié `models/`.
5. Génération de la config d'installation et du journal d'audit.
6. Signature du binaire pour Windows et validation sur machine vierge.

## Fichier de référence

- `scripts/build_nyx_installer.py`

## Sécurité

L'installateur doit :

- n'écrire que dans des emplacements explicites,
- créer le dossier d'installation local,
- ne pas dépendre d'un service cloud,
- exposer un journal d'installation séparé du journal d'usage.
