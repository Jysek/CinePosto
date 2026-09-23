"""Fusione dei film duplicati già presenti nel database.

Uso (nel container backend):

    python -m app.maintenance.dedup_films                  # DRY-RUN + report
    python -m app.maintenance.dedup_films --apply          # applica il piano
    python -m app.maintenance.dedup_films --merge 40:52    # fusione approvata a mano, ripetibile

Le fusioni avvengono solo per regole esplicite (stessa chiave ricalcolata, anno NULL
adottato, stesso wikidata_id, coppia --merge). I titoli semplicemente *simili* NON
vengono uniti: finiscono fra i candidati del report e si approvano uno a uno con
--merge (è la classe delle varianti di titolo fra fonti diverse, fase 13).

Senza --apply non scrive nulla. Con --apply c'è UN solo commit alla fine;
su qualsiasi eccezione rollback, il database resta come era.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime
from itertools import combinations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models.film import Film
from app.models.showing import Showing
from app.repositories.film_repo import normalize_title

# Soglia in edit distance sulle chiavi normalizzate, per i soli CANDIDATI:
# due titoli così vicini probabilmente sono lo stesso film, ma la fusione non è
# automatica — si approva con --merge. Contano anche i casi in cui una chiave è
# l'altra più un suffisso di parole (es. «X» / «X AL CINEMA»). Le regole certe
# sono quelle dei gruppi.
MAX_EDIT_DISTANCE_CANDIDATES = 2

RULE_KEY_YEAR = "stessa chiave ricalcolata + stesso anno"
RULE_KEY_NULL_YEAR = "stessa chiave ricalcolata, anno NULL adottato"
RULE_WIKIDATA = "stesso wikidata_id"
RULE_MANUAL = "fusione esplicita --merge"

# Campi metadati che il superstite può adottare dal film fuso (solo se lui non li ha).
FILL_FIELDS = (
    "original_title",
    "year",
    "runtime_minutes",
    "genres",
    "director",
    "poster_url",
    "synopsis",
    "wikidata_id",
)
# Campi che contano per la scelta deterministica del superstite (regola 5).
METADATA_FIELDS = ("poster_url", "synopsis", "director")

# Lunghezza massima di un valore nei messaggi di conflitto del report.
MAX_REPORT_VALUE = 60


@dataclass(frozen=True)
class FilmInfo:
    """Fotografia in sola lettura di una riga di `films`, con la chiave ricalcolata."""

    id: int
    title: str
    old_key: str
    new_key: str
    year: int | None
    original_title: str | None
    runtime_minutes: int | None
    genres: str | None
    director: str | None
    poster_url: str | None
    synopsis: str | None
    wikidata_id: str | None
    showing_count: int = 0

    @property
    def metadata_count(self) -> int:
        """Quanti metadati valorizzati ha la riga (regola 5.4)."""
        return sum(1 for name in METADATA_FIELDS if getattr(self, name) is not None)

    def get(self, name: str):
        """Valore di un campo per nome (usato dai riempimenti di fusione)."""
        return getattr(self, name)

    def describe(self) -> str:
        """Riga di report leggibile per questa riga di film."""
        year = self.year if self.year is not None else "anno NULL"
        wiki = self.wikidata_id if self.wikidata_id else "wikidata —"
        return f"#{self.id} «{self.title}» — {year}, {self.showing_count} showings, {wiki}"


@dataclass(frozen=True)
class ShowingInfo:
    """Fotografia in sola lettura di una riga di `showings`."""

    id: int
    film_id: int
    cinema_slug: str
    date: date_type
    times: str
    scraped_at: datetime


@dataclass(frozen=True)
class ShowingMove:
    """Uno showing che passa dal film perdente al superstite."""

    showing: ShowingInfo
    to_film_id: int


@dataclass(frozen=True)
class DiscardedShowing:
    """Uno showing scartato per collisione: resta la run più recente."""

    dropped: ShowingInfo
    kept: ShowingInfo


@dataclass
class MergeGroup:
    """Un gruppo di film da fondere (o da decidere, se `block_reason` è valorizzato)."""

    rule: str
    members: list[FilmInfo]
    note: str = ""
    block_reason: str = ""
    adoptions: dict[str, object] = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)
    moves: list[ShowingMove] = field(default_factory=list)
    discards: list[DiscardedShowing] = field(default_factory=list)

    @property
    def survivor(self) -> FilmInfo:
        """La riga che sopravvive alla fusione (scelta deterministica, regola 5)."""
        return pick_survivor(self.members)


@dataclass
class DedupPlan:
    """Piano completo: cosa verrebbe ricalcolato, fuso, scartato, segnalato."""

    total_films: int
    total_showings: int
    key_changes: list[FilmInfo]
    frozen: list[FilmInfo]
    groups: list[MergeGroup]
    undecided: list[MergeGroup]
    candidates: list[tuple[FilmInfo, FilmInfo, str]]


def edit_distance(a: str, b: str) -> int:
    """Distanza di Levenshtein: numero minimo di modifiche per trasformare a in b."""
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (char_a != char_b)))
        previous = current
    return previous[-1]


def pick_survivor(members: list[FilmInfo]) -> FilmInfo:
    """Scelta deterministica della riga che sopravvive, nell'ordine:
    1. più showings in totale; 2. `year` non nullo; 3. `wikidata_id` presente;
    4. più metadati (poster_url, synopsis, director); 5. id più basso.
    """
    ranked = sorted(
        members,
        key=lambda f: (-f.showing_count, f.year is None, f.wikidata_id is None, -f.metadata_count, f.id),
    )
    return ranked[0]


def load_snapshots(db: Session) -> tuple[list[FilmInfo], list[ShowingInfo]]:
    """Legge film e showings in sola lettura, con la chiave ricalcolata per ogni film."""
    films_orm = list(db.scalars(select(Film).order_by(Film.id)))
    showings_orm = list(db.scalars(select(Showing).order_by(Showing.id)))

    counts: dict[int, int] = {}
    for row in showings_orm:
        counts[row.film_id] = counts.get(row.film_id, 0) + 1

    films = [
        FilmInfo(
            id=row.id,
            title=row.title,
            old_key=row.title_normalized,
            new_key=normalize_title(row.title),
            year=row.year,
            original_title=row.original_title,
            runtime_minutes=row.runtime_minutes,
            genres=row.genres,
            director=row.director,
            poster_url=row.poster_url,
            synopsis=row.synopsis,
            wikidata_id=row.wikidata_id,
            showing_count=counts.get(row.id, 0),
        )
        for row in films_orm
    ]
    showings = [
        ShowingInfo(
            id=row.id,
            film_id=row.film_id,
            cinema_slug=row.cinema_slug,
            date=row.date,
            times=row.times,
            scraped_at=row.scraped_at,
        )
        for row in showings_orm
    ]
    return films, showings


def _conflict_reason(members: list[FilmInfo]) -> str:
    """Motivo per NON fondere in automatico: metadati in conflitto evidente (regola 7)."""
    wikis = sorted({m.wikidata_id for m in members if m.wikidata_id})
    if len(wikis) > 1:
        return "wikidata_id in conflitto: " + ", ".join(wikis)
    years = sorted({m.year for m in members if m.year is not None})
    if len(years) > 1:
        return "anni in conflitto: " + ", ".join(str(y) for y in years)
    return ""


def _plan_fills(group: MergeGroup) -> None:
    """Cosa il superstite adotta dal fuso (solo campi NULL) e cosa resta in conflitto."""
    survivor = group.survivor
    losers = sorted((m for m in group.members if m.id != survivor.id), key=lambda f: f.id)
    for name in FILL_FIELDS:
        current = survivor.get(name)
        values = [(m.id, m.get(name)) for m in losers if m.get(name) is not None]
        if not values:
            continue
        if current is None:
            group.adoptions[name] = values[0][1]
            distinct = {v for _, v in values}
            if len(distinct) > 1:
                group.conflicts.append(f"{name}: valori diversi fra i fusi, adottato il primo ({_short(values[0][1])})")
        elif any(v != current for _, v in values):
            lost = ", ".join(f"#{fid}={_short(v)}" for fid, v in values if v != current)
            group.conflicts.append(f"{name}: tenuto {_short(current)}, scartato {lost}")


def _short(value: object) -> str:
    """Valore reso leggibile nel report: le stringhe lunghe si accorciano."""
    text = repr(value)
    return text if len(text) <= MAX_REPORT_VALUE else text[: MAX_REPORT_VALUE - 1] + "…"


def _split_by_year(key: str, members: list[FilmInfo]) -> list[MergeGroup]:
    """Raggruppa per anno dentro la stessa chiave ricalcolata (regole 1 e 2)."""
    nulls = [f for f in members if f.year is None]
    valued: dict[int, list[FilmInfo]] = {}
    for f in members:
        if f.year is not None:
            valued.setdefault(f.year, []).append(f)

    if nulls and len(valued) == 1:
        # L'anno NULL incontra l'unico anno valorizzato: lo adotta (alta certezza).
        year, bucket = next(iter(valued.items()))
        merged = sorted([*nulls, *bucket], key=lambda f: f.id)
        return [MergeGroup(RULE_KEY_NULL_YEAR, merged, note=f"chiave «{key}», anno adottato: {year}")]

    groups = []
    for year, bucket in sorted(valued.items()):
        if len(bucket) > 1:
            groups.append(
                MergeGroup(RULE_KEY_YEAR, sorted(bucket, key=lambda f: f.id), note=f"chiave «{key}», anno {year}")
            )
    if len(nulls) > 1:
        group = MergeGroup(RULE_KEY_YEAR, sorted(nulls, key=lambda f: f.id), note=f"chiave «{key}», anno NULL")
        if len(valued) > 1:
            # Più anni candidati per la stessa chiave: quale dei remake è? Non si inventa.
            group.block_reason = f"anno NULL con più anni candidati ({sorted(valued)}) per la chiave «{key}»"
        groups.append(group)
    return groups


def _group_by_key(films: list[FilmInfo], claimed: set[int]) -> tuple[list[MergeGroup], list[MergeGroup]]:
    """Regole 1 e 2: stessa chiave ricalcolata (con anno uguale o NULL adottato)."""
    by_key: dict[str, list[FilmInfo]] = {}
    for f in films:
        if f.id not in claimed:
            by_key.setdefault(f.new_key, []).append(f)

    groups: list[MergeGroup] = []
    undecided: list[MergeGroup] = []
    for key in sorted(by_key):
        members = by_key[key]
        if len(members) < 2:
            continue
        for group in _split_by_year(key, members):
            group.block_reason = group.block_reason or _conflict_reason(group.members)
            (undecided if group.block_reason else groups).append(group)
    return groups, undecided


def _group_by_wikidata(films: list[FilmInfo], claimed: set[int]) -> tuple[list[MergeGroup], list[MergeGroup]]:
    """Regola 3: stesso `wikidata_id` (identità esterna forte, anche con chiavi diverse)."""
    by_wiki: dict[str, list[FilmInfo]] = {}
    for f in films:
        if f.id not in claimed and f.wikidata_id:
            by_wiki.setdefault(f.wikidata_id, []).append(f)

    groups: list[MergeGroup] = []
    undecided: list[MergeGroup] = []
    for wiki in sorted(by_wiki):
        members = by_wiki[wiki]
        if len(members) < 2:
            continue
        group = MergeGroup(RULE_WIKIDATA, sorted(members, key=lambda f: f.id), note=f"wikidata_id={wiki}")
        group.block_reason = _conflict_reason(group.members)
        (undecided if group.block_reason else groups).append(group)
    return groups, undecided


def _group_manual(by_id: dict[int, FilmInfo], pairs: list[tuple[int, int]]) -> list[MergeGroup]:
    """Regola 4: coppie approvate a mano con --merge (anche con chiavi diverse)."""
    for a, b in pairs:
        for film_id in (a, b):
            if film_id not in by_id:
                raise ValueError(f"film #{film_id} inesistente: --merge accetta id presenti nella tabella films")

    parent: dict[int, int] = {}

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for a, b in pairs:
        for film_id in (a, b):
            parent.setdefault(film_id, film_id)
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    clusters: dict[int, list[int]] = {}
    for film_id in parent:
        clusters.setdefault(find(film_id), []).append(film_id)

    groups = []
    for ids in sorted(clusters.values(), key=lambda ids: ids[0]):
        members = sorted((by_id[i] for i in ids), key=lambda f: f.id)
        groups.append(MergeGroup(RULE_MANUAL, members, note="--merge " + ":".join(str(i) for i in sorted(ids))))
    return groups


def _plan_group_showings(group: MergeGroup, by_film: dict[int, list[ShowingInfo]]) -> None:
    """Collisioni di showings dentro un gruppo: vince la run con `scraped_at` più recente."""
    survivor = group.survivor
    claimed = {(s.cinema_slug, s.date): s for s in by_film.get(survivor.id, [])}
    moves: dict[int, ShowingMove] = {}
    losers = sorted((m for m in group.members if m.id != survivor.id), key=lambda f: f.id)
    for loser in losers:
        for showing in sorted(by_film.get(loser.id, []), key=lambda s: s.id):
            slot = (showing.cinema_slug, showing.date)
            seated = claimed.get(slot)
            if seated is None:
                claimed[slot] = showing
                moves[showing.id] = ShowingMove(showing, survivor.id)
                continue
            # Parità di scraped_at: resta seduto (stabilità, nessuna scelta casuale).
            if showing.scraped_at > seated.scraped_at:
                dropped, kept = seated, showing
                claimed[slot] = showing
                moves[showing.id] = ShowingMove(showing, survivor.id)
            else:
                dropped, kept = showing, seated
            moves.pop(dropped.id, None)
            group.discards.append(DiscardedShowing(dropped, kept))
    group.moves = sorted(moves.values(), key=lambda m: m.showing.id)


def _candidate_reason(first: str, second: str) -> str | None:
    """Perché due chiavi diverse sono solo CANDIDATE (mai fuse in automatico).

    Motivi riconosciuti: edit distance ≤ MAX_EDIT_DISTANCE_CANDIDATES, oppure
    una chiave è l'altra più un suffisso di parole («X» / «X AL CINEMA»).
    I titoli italiani completamente diversi per lo stesso film non ricadono qui:
    restano fuori da ogni regola sulle stringhe, è il caso da chiudere a valle.
    """
    shorter, longer = sorted((first, second), key=len)
    distance = edit_distance(first, second)
    if 0 < distance <= MAX_EDIT_DISTANCE_CANDIDATES:
        return f"distanza {distance}"
    if longer.startswith(shorter + " "):
        return "una è l'altra più un suffisso di parole"
    return None


def _find_candidates(
    films: list[FilmInfo],
    groups: list[MergeGroup],
    undecided: list[MergeGroup],
) -> list[tuple[FilmInfo, FilmInfo, str]]:
    """Regola 5 (solo segnalazione): chiavi diverse ma quasi uguali, mai fuse qui."""
    group_of: dict[int, int] = {}
    for index, group in enumerate([*groups, *undecided]):
        for member in group.members:
            group_of[member.id] = index

    by_key: dict[str, list[FilmInfo]] = {}
    for f in films:
        by_key.setdefault(f.new_key, []).append(f)
    reps = [sorted(members, key=lambda f: f.id)[0] for _, members in sorted(by_key.items())]

    candidates = []
    for first, second in combinations(reps, 2):
        same_group = group_of.get(first.id) is not None and group_of.get(first.id) == group_of.get(second.id)
        reason = _candidate_reason(first.new_key, second.new_key)
        if reason is not None and not same_group:
            candidates.append((first, second, reason))
    return candidates


def _plan_keys(groups: list[MergeGroup], survivors: list[FilmInfo]) -> tuple[list[FilmInfo], list[FilmInfo]]:
    """Chiavi da ricalcolare da `title`; quelle che collidono restano com'erano."""
    adopted_year: dict[int, int | None] = {}
    for group in groups:
        if "year" in group.adoptions:
            adopted_year[group.survivor.id] = group.adoptions["year"]

    buckets: dict[tuple[str, int | None], list[FilmInfo]] = {}
    for film in survivors:
        final = (film.new_key, adopted_year.get(film.id, film.year))
        buckets.setdefault(final, []).append(film)

    key_changes: list[FilmInfo] = []
    frozen: list[FilmInfo] = []
    for members in sorted(buckets.values(), key=lambda ms: ms[0].id):
        for film in sorted(members, key=lambda f: f.id):
            if film.new_key == film.old_key:
                continue
            # Due superstiti con la stessa chiave finale: ricalcolare violerebbe la
            # UNIQUE. Restano con la chiave vecchia e il report lo dice.
            (frozen if len(members) > 1 else key_changes).append(film)
    return key_changes, frozen


def build_plan(
    films: list[FilmInfo],
    showings: list[ShowingInfo],
    manual_pairs: list[tuple[int, int]] = (),
) -> DedupPlan:
    """Costruisce il piano di fusione. Funzione pura: non guarda il database."""
    by_id = {f.id: f for f in films}
    manual = _group_manual(by_id, list(manual_pairs))
    claimed = {m.id for g in manual for m in g.members}

    key_groups, key_undecided = _group_by_key(films, claimed)
    claimed |= {m.id for g in [*key_groups, *key_undecided] for m in g.members}
    wiki_groups, wiki_undecided = _group_by_wikidata(films, claimed)

    groups = [*manual, *key_groups, *wiki_groups]
    undecided = [*key_undecided, *wiki_undecided]
    by_film: dict[int, list[ShowingInfo]] = {}
    for s in showings:
        by_film.setdefault(s.film_id, []).append(s)
    for group in groups:
        _plan_fills(group)
        _plan_group_showings(group, by_film)

    losers = {m.id for g in groups for m in g.members if m.id != g.survivor.id}
    survivors = [f for f in films if f.id not in losers]
    key_changes, frozen = _plan_keys(groups, survivors)

    return DedupPlan(
        total_films=len(films),
        total_showings=len(showings),
        key_changes=key_changes,
        frozen=frozen,
        groups=groups,
        undecided=undecided,
        candidates=_find_candidates(films, groups, undecided),
    )


def _set_temporary_keys(db: Session, plan: DedupPlan) -> None:
    """Prima le chiavi verso un valore unico temporaneo: nessuna collisione in mezzo."""
    for film in plan.key_changes:
        db.get(Film, film.id).title_normalized = f"__dedup_tmp_{film.id}__"
    db.flush()


def _apply_showings(db: Session, plan: DedupPlan) -> None:
    """Scarta gli showings perdenti e ri-assegna quelli che sopravvivono."""
    for record in sorted((d for g in plan.groups for d in g.discards), key=lambda d: d.dropped.id):
        db.delete(db.get(Showing, record.dropped.id))
        db.flush()  # libera la UNIQUE (film_id, cinema_slug, date) prima delle riassegnazioni
    for move in sorted((m for g in plan.groups for m in g.moves), key=lambda m: m.showing.id):
        db.get(Showing, move.showing.id).film = db.get(Film, move.to_film_id)
    db.flush()


def _merge_group(db: Session, group: MergeGroup) -> None:
    """Fonde un gruppo: spariscono i perdenti, il superstite adotta ciò che gli manca."""
    survivor = group.survivor
    for member in sorted(group.members, key=lambda f: f.id):
        if member.id != survivor.id:
            db.delete(db.get(Film, member.id))
    db.flush()  # i perdenti spariscono prima di scrivere sul superstite
    film = db.get(Film, survivor.id)
    for name, value in group.adoptions.items():
        setattr(film, name, value)
    db.flush()


def execute_plan(db: Session, plan: DedupPlan) -> None:
    """Applica il piano in UNA transazione. Su eccezione: rollback dal chiamante."""
    _set_temporary_keys(db, plan)
    _apply_showings(db, plan)
    for group in plan.groups:
        _merge_group(db, group)
    for film in plan.key_changes:
        db.get(Film, film.id).title_normalized = film.new_key
    db.flush()
    db.commit()


def _format_group(group: MergeGroup, index: int) -> list[str]:
    """Sezione di report per un gruppo (fuso o da decidere)."""
    lines = [f"  [{index}] {group.rule}" + (f" — {group.note}" if group.note else "")]
    survivor = group.survivor
    lines.append(f"      sopravvive: {survivor.describe()}")
    for member in sorted(group.members, key=lambda f: f.id):
        if member.id != survivor.id:
            lines.append(f"      si fonde:   {member.describe()}")
    if group.block_reason:
        lines.append(f"      BLOCCO: {group.block_reason}")
        return lines
    if group.adoptions:
        detail = ", ".join(f"{name}={_short(value)}" for name, value in sorted(group.adoptions.items()))
        lines.append(f"      metadati adottati dal fuso: {detail}")
    for conflict in group.conflicts:
        lines.append(f"      conflitto (tieni il superstite): {conflict}")
    lines.append(f"      showings ri-assegnati: {len(group.moves)}")
    if group.discards:
        lines.append(f"      showings scartati (vince la run più recente): {len(group.discards)}")
        for record in group.discards:
            dropped, kept = record.dropped, record.kept
            lines.append(
                f"        {dropped.cinema_slug} {dropped.date} {dropped.times} (run {_stamp(dropped.scraped_at)})"
                f" → tenuto {kept.times} (run {_stamp(kept.scraped_at)})"
            )
    return lines


def _stamp(when: datetime) -> str:
    """Data e ora della run di scraping, per il report."""
    return when.strftime("%Y-%m-%d %H:%M")


def _plural(count: int, singular: str, plural: str) -> str:
    """Numero con nome giusto al plurale italiano."""
    return f"{count} {singular if count == 1 else plural}"


def format_report(plan: DedupPlan, applied: bool) -> str:
    """Report completo del piano, in italiano."""
    mode = (
        "APPLICATO — 1 transazione, 1 commit"
        if applied
        else "DRY-RUN — nessuna modifica scritta (usa --apply per applicare il piano)"
    )
    lines = [
        "=== Manutenzione film duplicati ===",
        f"Modalità: {mode}",
        f"Database: {plan.total_films} film, {plan.total_showings} showings",
        "",
        f"-- Chiavi da ricalcolare: {len(plan.key_changes)}",
    ]
    for film in plan.key_changes:
        lines.append(f'  #{film.id} «{film.title}»: "{film.old_key}" → "{film.new_key}"')
    for film in plan.frozen:
        lines.append(
            f'  #{film.id} «{film.title}»: chiave NON ricalcolata — "{film.new_key}" collide con un\'altra riga superstite'
        )

    lines.append("")
    lines.append(f"-- Gruppi da fondere: {len(plan.groups)}")
    for index, group in enumerate(plan.groups, start=1):
        lines.extend(_format_group(group, index))

    lines.append("")
    lines.append(f"-- Da decidere (nessuna fusione automatica): {len(plan.undecided)}")
    for index, group in enumerate(plan.undecided, start=1):
        lines.extend(_format_group(group, index))

    lines.append("")
    lines.append(f"-- Candidati per somiglianza (NON fusi: servono --merge): {len(plan.candidates)}")
    for first, second, reason in plan.candidates:
        lines.append(f"  #{first.id} «{first.title}» ↔ #{second.id} «{second.title}» ({reason})")

    rows_to_merge = sum(len(g.members) for g in plan.groups)
    rows_removed = sum(len(g.members) - 1 for g in plan.groups)
    moves = sum(len(g.moves) for g in plan.groups)
    discards = sum(len(g.discards) for g in plan.groups)
    lines.append("")
    lines.append(
        f"-- Riepilogo: {_plural(len(plan.groups), 'gruppo', 'gruppi')}, "
        f"{_plural(rows_to_merge, 'riga da unire', 'righe da unire')}, "
        f"{_plural(moves, 'showing ri-assegnato', 'showings ri-assegnati')}, "
        f"{_plural(rows_removed, 'riga rimossa', 'righe rimosse')}, "
        f"{_plural(discards, 'showing scartato', 'showings scartati')}."
    )
    return "\n".join(lines)


def run_maintenance(db: Session, apply: bool = False, manual_pairs: list[tuple[int, int]] = ()) -> str:
    """Piano di dedup + report. Scritto solo con `apply=True`, in una transazione sola."""
    films, showings = load_snapshots(db)
    plan = build_plan(films, showings, manual_pairs)
    if apply:
        try:
            execute_plan(db, plan)
        except Exception:
            db.rollback()
            raise
    return format_report(plan, applied=apply)


def _parse_manual_pairs(raw_pairs: list[str]) -> list[tuple[int, int]]:
    """Valida `--merge A:B`: due id interi diversi. Fallisce subito, con messaggio chiaro."""
    pairs = []
    for raw in raw_pairs:
        parts = raw.split(":")
        if len(parts) != 2 or not all(part.strip().isdigit() for part in parts):
            raise ValueError(f"--merge accetta una coppia di id, es. --merge 40:52 (ricevuto: {raw!r})")
        first, second = (int(part) for part in parts)
        if first == second:
            raise ValueError(f"--merge richiede due id diversi (ricevuto: {raw!r})")
        pairs.append((first, second))
    return pairs


def main() -> None:
    """Uso standalone: python -m app.maintenance.dedup_films [--apply] [--merge A:B]"""
    parser = argparse.ArgumentParser(description="Fonde i film duplicati del database (dry-run di default).")
    parser.add_argument("--apply", action="store_true", help="applica il piano (senza: solo report, nessuna scrittura)")
    parser.add_argument(
        "--merge", action="append", default=[], metavar="A:B", help="fusione esplicita di due id film, ripetibile"
    )
    args = parser.parse_args()

    # In dev l'engine stampa le query SQL (echo=True): per un tool di report sono rumore.
    # L'InstanceLogger di SQLAlchemy ignora i livelli logging, va spento il flag echo.
    engine.echo = False
    engine.logger.echo = False
    try:
        pairs = _parse_manual_pairs(args.merge)
        with SessionLocal() as db:
            print(run_maintenance(db, apply=args.apply, manual_pairs=pairs))
    except ValueError as exc:
        raise SystemExit(f"Errore: {exc}")


if __name__ == "__main__":
    main()
