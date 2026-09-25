"""Data access layer: query su Film."""

from datetime import date as date_type
import logging
import re
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.film import Film
from app.models.showing import Showing

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """Trasforma un titolo in forma normalizzata per dedup.
    Es: 'Ricchi…da morire – Delitti in famiglia' → 'ricchi da morire delitti in famiglia'
    Regole:
    - `&` → `e`: UCI scrive "AMORI & INCANTESIMI 2", The Space "Amori e incantesimi 2":
      senza questa regola sono due film diversi per la chiave naturale del DB.
    - lowercase
    - accenti rimossi (NFKD + drop combining chars)
    - punteggiatura → spazio
    - spazi multipli collassati
    """
    nfkd = unicodedata.normalize("NFKD", title)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    # `&` = "e" in italiano. Va fatto PRIMA di sostituire la punteggiatura con spazi,
    # altrimenti la congiunzione sparisce e le due forme non si incontrano mai.
    ascii_only = ascii_only.replace("&", " e ")
    no_punct = re.sub(r"[^\w\s]", " ", ascii_only.lower(), flags=re.UNICODE)
    collapsed = re.sub(r"\s+", " ", no_punct).strip()
    return collapsed


def get_by_id(db: Session, film_id: int) -> Film | None:
    """Ritorna il film con la PK data, o None se non esiste (o è archiviato).

    È una lettura pubblica (dettaglio film nell'app): un film archiviato non deve
    comparire. Per il lookup del seed serve invece `get_by_natural_key`, che li
    trova tutti — è così che una riga archiviata si riattiva.
    """
    stmt = select(Film).where(Film.id == film_id, Film.removed_at.is_(None))
    return db.scalars(stmt).one_or_none()


def get_by_natural_key(db: Session, title_normalized: str, year: int | None) -> Film | None:
    """Cerca per la chiave naturale (title_normalized, year). Usato dal seed.

    Regole:
    - match esatto su (title_normalized, year);
    - un anno NULL è **jolly solo se il candidato è unico**: "non so ancora che film è"
      incontra l'anno valorizzato, ma se i candidati sono più di uno (remake omonimi)
      non si inventa nulla e si ritorna None.
    """
    stmt = select(Film).where(Film.title_normalized == title_normalized)
    rows = list(db.scalars(stmt))

    for film in rows:
        if film.year == year:
            return film

    compatible = [f for f in rows if f.year is None or year is None]
    if len(compatible) == 1:
        return compatible[0]
    return None


def get_by_wikidata(db: Session, wikidata_id: str) -> Film | None:
    """Cerca la riga che possiede quel `wikidata_id`. Usato dal seed.

    Vede anche le righe archiviate (come `get_by_natural_key`): è così che un film
    tornato in programmazione con un'altra forma di titolo riusa la sua riga storica.
    """
    stmt = select(Film).where(Film.wikidata_id == wikidata_id).order_by(Film.id)
    rows = list(db.scalars(stmt))
    if len(rows) > 1:
        # Impossibile per UNIQUE(wikidata_id): se succede il vincolo è stato
        # bypassato a mano. Si segnala e si usa la riga più vecchia.
        logger.warning(
            "Più righe con lo stesso wikidata_id %s: si usa la più vecchia (id %d)",
            wikidata_id,
            rows[0].id,
        )
    return rows[0] if rows else None


def search_by_title(db: Session, query: str, limit: int = 20) -> list[Film]:
    """Ricerca 'contains' sul titolo normalizzato. Esclude gli archiviati."""
    q_norm = normalize_title(query)
    stmt = (
        select(Film)
        .where(Film.removed_at.is_(None), Film.title_normalized.like(f"%{q_norm}%"))
        .order_by(Film.title)
        .limit(limit)
    )
    return list(db.scalars(stmt))


def list_in_programming(db: Session, date_from: date_type, date_to: date_type) -> list[Film]:
    """Film con almeno uno spettacolo tra date_from e date_to (inclusi).
    JOIN con showings + DISTINCT per evitare duplicati.
    Solo righe attive: un film archiviato o uno spettacolo archiviato non conta
    come "in programmazione".
    """
    stmt = (
        select(Film)
        .join(Showing, Showing.film_id == Film.id)
        .where(
            Film.removed_at.is_(None),
            Showing.removed_at.is_(None),
            Showing.date >= date_from,
            Showing.date <= date_to,
        )
        .order_by(Film.title)
        .distinct()
    )
    return list(db.scalars(stmt))


# Metadati aggiornati in tutti i rami dell'upsert (i null del JSON non sovrascrivono).
# `wikidata_id` non è in questa lista: si scrive solo quando è libero — vedi la
# tabella dei casi di `upsert_from_scraper`.
METADATA_FIELDS = ("original_title", "runtime_minutes", "genres", "director", "poster_url", "synopsis")


def _update_metadata(film: Film, data: dict) -> None:
    """Aggiorna i soli metadati non-null del payload su una riga esistente."""
    for key in METADATA_FIELDS:
        if data.get(key) is not None:
            setattr(film, key, data[key])


def upsert_from_scraper(db: Session, data: dict) -> Film:
    """Insert or update per Film. Usato dal seed_from_json.

    Il JSON scraper NON ha `title_normalized` né `year` come chiave —
    li ricaviamo qui. Torna sempre un Film con `.id` popolato (serve per FK).

    Identità a due segnali — un film = una riga:

    - `N = get_by_natural_key(title_normalized, year)` (come sempre, anno jolly incluso);
    - `W = get_by_wikidata(wikidata_id)`, solo se il payload porta un `wikidata_id`;
      vede anche le righe archiviate, come `get_by_natural_key`.

    | N | W | cosa si fa |
    |---|---|---|
    | riga | stessa riga oppure W = None | upsert di sempre: metadati non-null + anno adottato |
    | None | riga | **riuso**: stesso film tornato con un'altra forma di titolo → metadati di W, mai INSERT |
    | riga | riga diversa | **conflitto**: solo metadati di N, nessuna scrittura di `wikidata_id`, mai INSERT |
    | None | None | INSERT (unico caso in cui si inserisce) |

    Il riuso via `wikidata_id` NON cambia la chiave naturale (`title_normalized`, `year`)
    né `title`: se una run futura ripropone la forma vecchia senza wikidata, il lookup per
    chiave deve continuare a trovare questa riga — ogni cambio di chiave riapre la porta
    ai doppioni. La chiave è interna: la sua stabilità vale più del titolo corrente.

    Il conflitto di identità non è un errore: il seed continua e la coppia si segnala a
    valle (`seed_from_json._identity_conflicts`) nel formato `dedup_films --merge A:B`.
    La fusione è una decisione umana: qui non si inserisce nulla e non si scrive un
    `wikidata_id` che è già di un'altra riga.

    `removed_at` non si tocca qui: chi decide se una riga è in programmazione o archiviata
    è la riconciliazione a fine import (`archive_not_in`/`reactivate_in`), che ragiona
    sull'insieme importato, non sul singolo record. La riga riusata via W finisce in
    `keep_keys` con la SUA chiave e quindi si riattiva come ogni altra.
    """
    title = data["title"]
    title_normalized = normalize_title(title)
    year = data.get("year")
    wikidata_id = data.get("wikidata_id")

    film = get_by_natural_key(db, title_normalized, year)
    owner = get_by_wikidata(db, wikidata_id) if wikidata_id is not None else None

    if film is None and owner is not None:
        # Riuso via wikidata: solo metadati, la chiave della riga resta quella di sempre.
        _update_metadata(owner, data)
        db.flush()
        return owner

    if film is None:
        # Nessun segnale collide: film nuovo.
        film = Film(
            title=title,
            title_normalized=title_normalized,
            original_title=data.get("original_title"),
            year=year,
            runtime_minutes=data.get("runtime_minutes"),
            genres=data.get("genres"),
            director=data.get("director"),
            poster_url=data.get("poster_url"),
            synopsis=data.get("synopsis"),
            wikidata_id=wikidata_id,
        )
        db.add(film)
        db.flush()  # forza l'assegnazione dell'id (serve al seed di showings)
        return film

    if owner is not None and owner.id != film.id:
        # Conflitto di identità: N e W sono righe diverse e il payload dice che sono
        # lo stesso film. Nessuna scrittura di `wikidata_id` (non su N, non su W):
        # si aggiornano i soli metadati di N e la coppia si segnala a valle.
        _update_metadata(film, data)
        db.flush()
        return film

    # N è la riga giusta: metadati non-null, `wikidata_id` scritto solo se è libero
    # (W = None, oppure W = N) e anno NULL della riga adottato — la chiave si completa,
    # non si duplica.
    _update_metadata(film, data)
    if wikidata_id is not None:
        film.wikidata_id = wikidata_id
    if film.year is None and year is not None:
        film.year = year

    db.flush()  # forza l'assegnazione dell'id (serve al seed di showings)
    return film


def archive_not_in(db: Session, keep_keys: set[tuple[str, int | None]]) -> int:
    """Archivia i film la cui chiave naturale non è fra quelle importate. Ritorna quanti.

    Archiviare = soft delete (`removed_at = now`): la riga resta nel DB con tutti i
    suoi dati e i suoi showings, ma sparisce dalle query pubbliche. È la regola
    decisa dall'utente — i dati non si cancellano mai, perché tra due anni lo stesso
    film può tornare in programmazione e i dati vecchi si vogliono riusare.
    Le righe già archiviate non si toccano: la data resta quella della prima uscita.
    """
    rows = list(db.scalars(select(Film).where(Film.removed_at.is_(None))))
    archived = 0
    for film in rows:
        if (film.title_normalized, film.year) not in keep_keys:
            film.removed_at = func.now()
            archived += 1
    return archived


def reactivate_in(db: Session, keep_keys: set[tuple[str, int | None]]) -> int:
    """Riattiva i film archiviati che ricompaiono fra le chiavi importate. Ritorna quanti.

    `removed_at` torna NULL: la riga torna visibile e i dati storici (creazione,
    showings passati) restano intatti.
    """
    rows = list(db.scalars(select(Film).where(Film.removed_at.is_not(None))))
    reactivated = 0
    for film in rows:
        if (film.title_normalized, film.year) in keep_keys:
            film.removed_at = None
            reactivated += 1
    return reactivated
