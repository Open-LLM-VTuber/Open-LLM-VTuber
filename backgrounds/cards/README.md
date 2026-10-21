# Tarot deck (Major Arcana)

`major_00.jpg` … `major_21.jpg` son los 22 arcanos mayores del mazo
**Rider–Waite–Smith**, dibujado por **Pamela Colman Smith** (1878–1951) y publicado
por primera vez en 1909.

- **Licencia:** dominio público (*PD-old-80-expired* en Wikimedia Commons,
  «Public domain» / «Copyrighted: False»). No exige atribución, pero conviene
  conservar este fichero.
- **Origen:** Wikimedia Commons, p. ej.
  <https://commons.wikimedia.org/wiki/File:RWS_Tarot_16_Tower.jpg>
- **Resolución:** miniaturas de 960 px de ancho (el bucket que expone el servicio
  de miniaturas), ~500 KB por carta.
- **Orden:** `major_NN` = arcano NN (`major_00` = El Loco, `major_21` = El Mundo),
  el mismo id que usa `src/open_llm_vtuber/utils/tarot.py`.

## Regenerar o sustituir

```powershell
powershell -ExecutionPolicy Bypass -File scripts/fetch_tarot_art.ps1 -Force
```

Para usar tu propio mazo, deja aquí `<id>.jpg` con los mismos nombres (o cambia
`CARD_ART_EXT` en `utils/tarot.py`). Los `.svg` que hay junto a los JPEG son el
**mazo de reserva** que genera `scripts/make_tarot_cards.py`: sirven si quieres
un juego sin dependencias de licencia:

```python
build_draw_props(drawn, art_ext="svg")
```
