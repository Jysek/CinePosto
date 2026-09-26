"""Title normalization, fuzzy matching (Levenshtein), and duration parsing."""

from __future__ import annotations

import re

_TITLE_SUFFIXES = re.compile(
    r"\s*[-–]\s*(3D|IMAX|HFR|4DX|ScreenX|EPIC|Dolby Atmos|Dolby Cinema|VIP|Gold|OV|VOST|VO|VF|Versione Originale|Sottotitolato|Sub ITA|Live|Event|F\&S|F&S|Family|Kids|Matinée|Sera|Notte)$",
    re.IGNORECASE,
)

_YEAR_SUFFIX = re.compile(r"\s*[\(\[]?\s*(?:19|20)\d{2}\s*[\)\]]?\s*$")

_ROMAN_NUM_SUFFIX = re.compile(r"\s+(I{1,3}V?|IV|VI{0,3}|IX|X{1,3}V?I{0,3}|XI{0,3})\s*$", re.IGNORECASE)

_RIEDITION_SUFFIX = re.compile(r"\s+4K\s*\(RIED\.?\s*\d{4}\)\s*(C\.A\.?)?\s*$", re.IGNORECASE)

_C_A_SUFFIX = re.compile(r"\s+C\.A\.?\s*$", re.IGNORECASE)

_AND_WORD = re.compile(r"\bAND\b", re.IGNORECASE)

_FRANCHISE_PREFIXES = re.compile(
    r"^(?:STAR WARS:\s*|MARVEL(?:'S)?\s+|DC\s+|PIXAR\s+|Disney\s+|THE\s+|IL\s+|LA\s+)",
    re.IGNORECASE,
)

_ARTICLES = {"il", "la", "lo", "le", "gli", "i", "un", "uno", "una", "di", "del", "della", "dei", "degli"}


def normalize_title(title: str) -> str:
    """Riduce un titolo alla forma canonica usata come id del film nei JSON.

    Rimuove il rumore che varia tra i siti dei cinema mantenendo il titolo
    leggibile: apostrofi/trattini tipografici → ASCII, suffissi di sala
    (3D, IMAX, VOS...), anno tra parentesi, marcatori di riedizione, prefissi
    di franchise e articoli iniziali. NON fa lowercase: per il confronto
    case-insensitive si usa `title_key()`.

    Le cifre finali NON si tagliano: un numero finale è parte del titolo
    («Amori e incantesimi 2» non è «Amori e incantesimi», è il suo sequel).
    Gli anni continuano a essere rimossi da `_YEAR_SUFFIX` (fra parentesi o
    parentesi quadre: «Dune (2021)»).
    """
    if not title:
        return ""
    t = title.strip()
    t = t.replace("\u2019", "'")
    t = t.replace("\u2018", "'")
    t = t.replace("\u201c", '"')
    t = t.replace("\u201d", '"')
    t = t.replace("\u2013", "-")
    t = t.replace("\u2014", "-")

    # _TITLE_SUFFIXES can stack ("Film - 3D - IMAX"); 3 passes strips up to 3 nested suffixes
    for _ in range(3):
        t = _TITLE_SUFFIXES.sub("", t).strip()

    t = _RIEDITION_SUFFIX.sub("", t).strip()

    t = _YEAR_SUFFIX.sub("", t).strip()

    t = _C_A_SUFFIX.sub("", t).strip()

    t = _AND_WORD.sub("", t).strip()

    t = _FRANCHISE_PREFIXES.sub("", t).strip()

    t = re.sub(r"\s+", " ", t)

    t = t.strip(" .,;:!?-–—")

    return t


def title_key(title: str) -> str:
    """Chiave di confronto aggressiva: minuscole, senza punteggiatura né spazi.

    Usata SOLO per i match tra titoli (mai mostrata o salvata): "Dune – Parte 2"
    e "DUNE parte 2" producono la stessa chiave.
    """
    normalized = normalize_title(title).lower()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def titles_match(a: str, b: str) -> bool:
    """Match esatto sulle chiavi normalizzate (nessuna tolleranza ai refusi)."""
    return title_key(a) == title_key(b)


def fuzzy_match(a: str, b: str) -> bool:
    """Match tollerante per la dedup cross-cinema: esatto, contenimento o Levenshtein.

    La soglia di edit distance scala con la lunghezza (1 refuso ogni 4 caratteri,
    minimo 2): abbastanza larga da unire "alien"/"alein", abbastanza stretta da
    non fondere film diversi. Eccezione stretta: se una chiave è l'altra più le
    cifre finali non si fonde — è il sequel numerato, non un refuso.
    """
    ka = title_key(a)
    kb = title_key(b)
    if ka == kb:
        return True
    if _is_numbered_sequel(ka, kb):
        return False
    if ka in kb or kb in ka:
        return True
    if _edit_distance(ka, kb) <= max(2, len(ka) // 4):  # 1 typo per 4 chars: "alien"~"alein" ok, not "avatar"~"avsdar"
        return True
    return False


def _is_numbered_sequel(ka: str, kb: str) -> bool:
    """True se una chiave è l'altra più le cifre finali ("x2" vs "x").

    Un numero finale è parte del titolo: «Amori e incantesimi 2» non è un
    refuso di «Amori e incantesimi», è un altro film. Toglie solo le cifre
    finali (maiuscole, punteggiatura e spazi sono già fuori da `title_key`),
    così la regola non tocca le altre differenze, che restano gestite dal
    contenimento e dalla distanza di edit.
    """
    if not ka or not kb:
        return False
    sa = ka.rstrip("0123456789")
    sb = kb.rstrip("0123456789")
    return sa == sb and (sa != ka or sb != kb)


def _edit_distance(s1: str, s2: str) -> int:
    """Levenshtein distance between two strings (iterative, O(n*m))."""
    if len(s1) < len(s2):
        return _edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(
                min(
                    prev_row[j + 1] + 1,
                    curr_row[j] + 1,
                    prev_row[j] + cost,
                )
            )
        prev_row = curr_row
    return prev_row[-1]


def normalize_genres(raw: list | str | None) -> list[str]:
    """Uniforma i generi alla forma lista di stringhe.

    Le fonti sono eterogenee: stringa CSV ("Drammatico, Thriller"), lista di
    stringhe, o lista di oggetti con campo `name` (API The Space).
    """
    if isinstance(raw, str):
        return [g.strip() for g in re.split(r"[,/]", raw) if g.strip()]
    if isinstance(raw, list):
        return [g if isinstance(g, str) else g.get("name", "") for g in raw if g]
    return []


_HMS_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")

_HOURS_MIN_RE = re.compile(r"(\d+)\s*h\s*(\d+)?\s*m?", re.IGNORECASE)


def normalize_duration(duration: str | None) -> str | None:
    """Uniforma la durata al formato canonico "N min".

    Accetta i formati delle varie fonti: "1:49:00" (H:M:S), "1h 49m", "109",
    "109 min". Ritorna None se non c'è nessun numero riconoscibile.
    """
    if not duration:
        return None

    s = str(duration).strip()
    if not s:
        return None

    m = _HMS_RE.match(s)
    if m:
        h = int(m.group(1))
        mn = int(m.group(2))
        sec = int(m.group(3) or 0)
        total = h * 60 + mn + (1 if sec >= 30 else 0)
        return f"{total} min"

    hm = _HOURS_MIN_RE.search(s)
    if hm:
        h = int(hm.group(1))
        mn = int(hm.group(2) or 0)
        total = h * 60 + mn
        return f"{total} min"

    nums = re.findall(r"\d+", s)
    if nums:
        return f"{int(nums[0])} min"

    return None


_TRUNCATED_TAIL = re.compile(r"(\.{3}|…)\s*$")


def is_truncated_description(text: str | None) -> bool:
    """True se la descrizione si chiude con i puntini di sospensione.

    Le meta description dei CMS sono tagliate a ~100 caratteri a metà parola e
    chiuse con "...": un testo così non è mai preferibile a uno intero.
    """
    return bool(text) and bool(_TRUNCATED_TAIL.search(text))


def pick_fuller_description(a: str | None, b: str | None) -> str | None:
    """Sceglie la descrizione più completa fra due, senza declassare quella buona.

    Ordine di preferenza: un testo non troncato batte un testo troncato; a pari
    troncamento vince il più lungo. `None` o stringa vuota perdono sempre.
    Serve a impedire che una sinossi intera venga sovrascritta dalla meta
    description tagliata di un'altra fonte (o di una run successiva).
    """
    if not a:
        return b
    if not b:
        return a
    truncated_a = is_truncated_description(a)
    truncated_b = is_truncated_description(b)
    if truncated_a != truncated_b:
        return b if truncated_a else a
    return a if len(a) >= len(b) else b
