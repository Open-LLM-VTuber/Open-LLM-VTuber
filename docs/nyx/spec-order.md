# Nyx — ordre des spécifications

Cette feuille de route suit la spec de référence `Nyx_Recette.pdf` et applique la méthode Spec Kit avant chaque implémentation.

## Ordre de dépendance obligatoire

1. Perception et incarnation
   - `/speckit.specify "Nyx perception and embodiment"`
   - `/speckit.plan "Nyx perception and embodiment"`
   - Livrable: voix ASR/TTS, interruption vocale, état interne en Live2D.

2. Mémoire et contexte
   - `/speckit.specify "Nyx memory and context retrieval"`
   - `/speckit.plan "Nyx memory and context retrieval"`
   - Livrable: mémoire de travail, épisodique, sémantique, recherche contextuelle.

3. Action locale
   - `/speckit.specify "Nyx local action runner"`
   - `/speckit.plan "Nyx local action runner"`
   - `/speckit.analyze "Nyx local action runner"`
   - Livrable: lecture/écriture de fichiers, exécution autorisée, surveillance de services, communication locale.

4. Évolution et auto-correction
   - `/speckit.specify "Nyx evolution and self-repair"`
   - `/speckit.plan "Nyx evolution and self-repair"`
   - `/speckit.analyze "Nyx evolution and self-repair"`
   - Livrable: diff lisible, validation, rollback, apprentissage par retour.

5. Gouvernance et audit
   - `/speckit.specify "Nyx governance and audit trail"`
   - `/speckit.plan "Nyx governance and audit trail"`
   - `/speckit.analyze "Nyx governance and audit trail"`
   - Livrable: périmètre, refus des actions hors cadre, journal séparé du chat.

6. Packaging et installation Windows
   - `/speckit.specify "Nyx Windows installer"`
   - `/speckit.plan "Nyx Windows installer"`
   - `/speckit.analyze "Nyx Windows installer"`
   - Livrable: .exe unique installant backend, dépendances, Open-LLM-VTuber et modèles localement.

## Règles d'implémentation

- Aucune ligne de code ne doit être ajoutée avant la spec et le plan de la fonctionnalité.
- Les modules touchant l'autonomie d'action ou l'auto-modification doivent être précédés de `/speckit.analyze`.
- L'implémentation doit se faire dans l'ordre de dépendance : Perception → Mémoire → Action → Évolution → Gouvernance → Packaging.
- Le point d'entrée final reste un installateur Windows unique, sans intervention manuelle.
