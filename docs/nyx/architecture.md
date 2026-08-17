# Nyx — architecture cible

## Mission

Nyx est une IA locale, incarnée et autonome, conçue comme un agent de travail sur machine Windows locale, sans dépendance cloud obligatoire.

## Bloc de base

- Open-LLM-VTuber : perception, voix, interruption, avatar Live2D.
- Mémoire locale : historique, contexte utile, faits stables.
- Runtime d'actions : fichiers, scripts, services, réseau local.
- Audit & gouvernance : journal d'actions distinct du chat, refus des actions hors périmètre.
- Packaging : installateur .exe unique et reproductible.

## Architecture logique

```text
+-------------------------------+
|  Nyx Runtime                  |
|  - state machine              |
|  - orchestration              |
|  - policy enforcement         |
+---------------+---------------+
                |
                v
+-------------------------------+
|  Perception Layer             |
|  - ASR / TTS                  |
|  - voice interruption         |
|  - Live2D state display       |
+-------------------------------+
                |
                v
+-------------------------------+
|  Memory Layer                 |
|  - working memory             |
|  - episodic memory            |
|  - semantic memory            |
|  - retrieval                  |
+-------------------------------+
                |
                v
+-------------------------------+
|  Action Layer                 |
|  - local filesystem           |
|  - commands / scripts         |
|  - services / monitors        |
|  - MQTT / local network       |
+-------------------------------+
                |
                v
+-------------------------------+
|  Evolution Layer              |
|  - self-review                |
|  - diff generation            |
|  - rollback / versioning      |
|  - learning by feedback       |
+-------------------------------+
                |
                v
+-------------------------------+
|  Governance Layer             |
|  - allowlist                  |
|  - audit log                  |
|  - refusal on out-of-scope    |
|  - spec gate before edits     |
+-------------------------------+
```

## Priorités de mise en œuvre

1. Stabiliser la couche Perception.
2. Stabiliser la couche Mémoire.
3. Stabiliser la couche Action.
4. Ajouter la couche d'Évolution.
5. Ajouter les garde-fous de Gouvernance.
6. Finaliser le Packaging Windows.

La dépendance entre Action et Évolution est stricte : aucune évolution autonome ne doit être autorisée avant que l'action locale soit auditée et sécurisée.
