"""Major Arcana deck and spreads for the scripted tarot show.

Standard library only, so the scheduler, the tests and
``scripts/export_overlay_fixtures.py`` can all use it without pydantic or
fastapi. The show is in Spanish, so the card names and readings are in Spanish
(the persona prompt already is).

Public API:

    draw_cards(count=1, seed=None)   -> list[DrawnCard]
    build_draw_props(drawn)          -> list[dict]  # ``label`` props, no art
    build_tarot_brief(drawn, q="")   -> str         # instruction for the LLM

The draw is reproducible when ``seed`` is given, which is what makes it
testable and what lets a job replay the same spread.
"""

from dataclasses import dataclass
from random import Random
from typing import Iterable, List, Optional, Sequence, Tuple

#: A reading is a one-card-of-the-day or a three-card spread. More than three
#: cards do not fit on the overlay without art.
MAX_CARDS = 3

#: Position names by spread size (see ``draw_cards``).
SPREAD_POSITIONS = {
    1: ("Carta del día",),
    2: ("Tú", "La situación"),
    3: ("Pasado", "Presente", "Futuro"),
}

#: id, name, keywords, upright reading, reversed reading.
_ARCANA: Sequence[Tuple[str, str, Tuple[str, ...], str, str]] = (
    (
        "major_00",
        "El Loco",
        ("comienzo", "impulso", "confianza"),
        "Un salto al vacío que abre camino: empieza sin tenerlo todo atado.",
        "Impulso sin rumbo: mira el suelo antes de saltar.",
    ),
    (
        "major_01",
        "El Mago",
        ("voluntad", "talento", "iniciativa"),
        "Tienes las herramientas: es momento de usarlas con intención.",
        "Talento disperso o promesas vacías: enfoca una sola cosa.",
    ),
    (
        "major_02",
        "La Sacerdotisa",
        ("intuición", "secreto", "calma"),
        "Lo importante todavía no se dice: escucha tu intuición.",
        "Te estás ocultando información, incluso de ti misma.",
    ),
    (
        "major_03",
        "La Emperatriz",
        ("abundancia", "cuidado", "creatividad"),
        "Algo crece si lo cuidas: tiempo de nutrir, no de exigir.",
        "Bloqueo creativo o cuidados que solo van hacia fuera.",
    ),
    (
        "major_04",
        "El Emperador",
        ("estructura", "límites", "autoridad"),
        "Pon orden y reglas claras: la estructura te sostiene.",
        "Rigidez o control excesivo: los límites ya no protegen.",
    ),
    (
        "major_05",
        "El Sumo Sacerdote",
        ("tradición", "aprendizaje", "consejo"),
        "Busca una guía con experiencia o vuelve a lo que ya sabes que funciona.",
        "Normas heredadas que ya no te representan.",
    ),
    (
        "major_06",
        "Los Enamorados",
        ("elección", "vínculo", "coherencia"),
        "Una decisión del corazón: elige lo que te deja en paz.",
        "Dudas o un vínculo que te obliga a traicionar tus valores.",
    ),
    (
        "major_07",
        "El Carro",
        ("avance", "dirección", "victoria"),
        "Coge las riendas: el avance depende de tu dirección, no de la suerte.",
        "Fuerzas que tiran en sentidos distintos: frena y vuelve a alinear.",
    ),
    (
        "major_08",
        "La Fuerza",
        ("templanza", "coraje", "paciencia"),
        "La fuerza real es suave: domina sin romper.",
        "Coraje gastado en luchar contra ti misma.",
    ),
    (
        "major_09",
        "El Ermitaño",
        ("pausa", "introspección", "soledad"),
        "Retírate un momento: la respuesta aparece en silencio.",
        "Aislamiento que ya no enseña nada: pide compañía.",
    ),
    (
        "major_10",
        "La Rueda de la Fortuna",
        ("cambio", "ciclo", "oportunidad"),
        "La rueda gira: lo que estaba quieto se mueve a tu favor.",
        "Resistencia al cambio: el ciclo sigue sin ti.",
    ),
    (
        "major_11",
        "La Justicia",
        ("equilibrio", "verdad", "consecuencia"),
        "Lo que siembras se pesa: actúa con honestidad y quedará en equilibrio.",
        "Algo desequilibrado que exige una conversación pendiente.",
    ),
    (
        "major_12",
        "El Colgado",
        ("pausa", "otra mirada", "entrega"),
        "Suspende la acción y mira desde otro ángulo: la pausa es la jugada.",
        "Sacrificio inútil: estás esperando de más.",
    ),
    (
        "major_13",
        "La Muerte",
        ("final", "transformación", "limpieza"),
        "Algo termina para dejar sitio: no es castigo, es poda.",
        "Un final que se alarga porque no lo aceptas.",
    ),
    (
        "major_14",
        "La Templanza",
        ("medida", "mezcla", "sanación"),
        "Dosifica: el progreso está en el término medio.",
        "Exceso o prisa: mezcla de nuevo con más calma.",
    ),
    (
        "major_15",
        "El Diablo",
        ("deseo", "atadura", "sombra"),
        "Nombra lo que te ata: el deseo también dice qué quieres.",
        "Una atadura que ya reconoces y todavía no sueltas.",
    ),
    (
        "major_16",
        "La Torre",
        ("ruptura", "verdad", "derrumbe"),
        "Cae lo que estaba mal construido: duele y libera a la vez.",
        "Un derrumbe que se evita a medias y vuelve más tarde.",
    ),
    (
        "major_17",
        "La Estrella",
        ("esperanza", "calma", "renacer"),
        "Después del ruido viene la calma: hay motivos para esperar.",
        "Esperanza baja: cuida el descanso antes de pedirte más.",
    ),
    (
        "major_18",
        "La Luna",
        ("intuición", "miedo", "sueño"),
        "No todo está claro y no hace falta: avanza con lo que intuyes.",
        "Miedo que inventa historias: separa lo real de lo imaginado.",
    ),
    (
        "major_19",
        "El Sol",
        ("claridad", "alegría", "éxito"),
        "Luz plena: lo que hagas se verá y se agradecerá.",
        "Alegría a medias o éxito que tarda un poco más.",
    ),
    (
        "major_20",
        "El Juicio",
        ("balance", "llamada", "despertar"),
        "Una llamada clara: revisa lo vivido y responde.",
        "Evitas mirar atrás y la decisión sigue esperando.",
    ),
    (
        "major_21",
        "El Mundo",
        ("cierre", "plenitud", "logro"),
        "Un ciclo se completa: reconoce lo conseguido.",
        "Un cierre pendiente que no te deja empezar lo siguiente.",
    ),
)


@dataclass(frozen=True)
class TarotCard:
    """One Major Arcana card."""

    id: str
    name: str
    keywords: Tuple[str, ...]
    upright: str
    reversed: str


@dataclass(frozen=True)
class DrawnCard:
    """A card as it came out of the deck, with its spread position."""

    card: TarotCard
    reversed: bool = False
    position: str = ""

    def label(self) -> str:
        """Title for the overlay card (``stage-update`` prop ``label``)."""
        return self.card.name

    def sublabel(self) -> str:
        """Keywords plus the orientation: short, it is drawn on stream."""
        words = list(self.card.keywords)
        if self.reversed:
            words.append("invertida")
        return " · ".join(words)

    def meaning(self) -> str:
        """One-line reading for the current orientation."""
        return self.card.reversed if self.reversed else self.card.upright

    def describe(self) -> str:
        """``"Pasado: El Loco (invertida)"``: used in the LLM brief."""
        suffix = " (invertida)" if self.reversed else ""
        if self.position:
            return f"{self.position}: {self.card.name}{suffix}"
        return f"{self.card.name}{suffix}"


DECK: Tuple[TarotCard, ...] = tuple(TarotCard(*row) for row in _ARCANA)


def deck_ids() -> List[str]:
    """All card ids, in deck order (used by the tests and the docs)."""
    return [card.id for card in DECK]


def card_by_id(card_id: str) -> Optional[TarotCard]:
    """Look a card up by id, or ``None``."""
    for card in DECK:
        if card.id == card_id:
            return card
    return None


def draw_cards(
    count: int = 1,
    *,
    seed: Optional[int] = None,
    allow_reversed: bool = True,
) -> List[DrawnCard]:
    """Draw ``count`` different cards, with their spread positions.

    Args:
        count: 1, 2 or 3 cards (``MAX_CARDS``).
        seed: makes the draw reproducible; ``None`` uses system randomness.
        allow_reversed: whether a card may come out upside down.

    Raises:
        ValueError: when ``count`` is not between 1 and ``MAX_CARDS``.
    """
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError(f"count must be an int, got {type(count).__name__}")
    if count < 1 or count > MAX_CARDS:
        raise ValueError(f"count must be between 1 and {MAX_CARDS}, got {count}")

    rng = Random(seed) if seed is not None else Random()
    cards = rng.sample(DECK, count)
    positions = SPREAD_POSITIONS[count]
    return [
        DrawnCard(
            card=card,
            reversed=bool(allow_reversed and rng.random() < 0.5),
            position=position,
        )
        for card, position in zip(cards, positions)
    ]


#: Horizontal slots per spread size, normalised 0..1 (stage contract).
_SPREAD_X = {1: (0.5,), 2: (0.36, 0.64), 3: (0.28, 0.5, 0.72)}
#: Cards sit low on the frame so the avatar keeps the upper half.
_SPREAD_Y = 0.68


def build_draw_props(drawn: Iterable[DrawnCard]) -> List[dict]:
    """Turn a spread into ``stage-update`` props (text cards, no art needed).

    The overlay draws ``label``/``sublabel`` inside a card-shaped box, so the
    show works before any card art exists. When the art arrives, the same
    positions accept ``src`` props without touching the scheduler.

    Raises:
        ValueError: when the spread size has no layout.
    """
    cards = list(drawn)
    if not cards:
        return []
    xs = _SPREAD_X.get(len(cards))
    if xs is None:
        raise ValueError(f"no layout for {len(cards)} cards")

    return [
        {
            "id": f"card_{index + 1}",
            "label": drawn_card.label(),
            "sublabel": drawn_card.sublabel(),
            "x": xs[index],
            "y": _SPREAD_Y,
        }
        for index, drawn_card in enumerate(cards)
    ]


def build_tarot_brief(drawn: Iterable[DrawnCard], question: str = "") -> str:
    """Instruction block that tells the LLM which cards came out.

    The scheduler puts it before ``job.text`` in the ``ai-speak-signal``
    payload, so the vtuber narrates the spread that is already on screen
    instead of inventing one.
    """
    cards = list(drawn)
    if not cards:
        return ""

    lines = ["[Tirada de tarot preparada por el sistema]"]
    cleaned = (question or "").strip()
    if cleaned:
        lines.append(f"Pregunta: {cleaned}")
    for drawn_card in cards:
        lines.append(f"- {drawn_card.describe()}. {drawn_card.meaning()}")
    lines.append(
        f"Interpreta esta tirada de {len(cards)} carta(s) en 3-5 frases, en "
        "español y mirando a cámara. No inventes otras cartas."
    )
    return "\n".join(lines)
