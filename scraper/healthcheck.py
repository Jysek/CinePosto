"""
Ping the primary endpoint of every connector (one per cinema) and report their status.

Usage (from CinemaScarper root):
    python healthcheck.py

Exit code 0 = all OK, 1 = at least one failure.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import sys
import time

import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[0]))

from scraper.config import (
    CINEMA_ZENITH_URL,
    CONCORDIA_URL,
    DEFAULT_USER_AGENT,
    METROPOLIS_URL,
    NUOVO_CASTELLO_URL,
    POSTMOD_CINEMA_URL,
    REQUEST_RETRY,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
    THE_SPACE_AUTH_URL,
    THE_SPACE_CINEMAS_URL,
    UCI_PROGRAMMING_URL,
)

TIMEOUT = REQUEST_TIMEOUT  # lo stesso limite che i connettori usano davvero

UA = DEFAULT_USER_AGENT


@dataclass
class CheckResult:
    cinema: str
    endpoint: str
    ok: bool
    status: int | None
    elapsed_ms: int
    error: str | None = None


def _attempt_request(method: str, url: str, **kwargs) -> CheckResult:
    """Un singolo tentativo HTTP: gli errori >= 400 sono un fatto, non un transient."""
    t0 = time.monotonic()
    headers = {"User-Agent": UA, **kwargs.pop("headers", {})}
    try:
        resp = getattr(requests, method)(url, timeout=TIMEOUT, headers=headers, **kwargs)
        elapsed = int((time.monotonic() - t0) * 1000)
        return CheckResult(
            cinema="",
            endpoint=url,
            ok=resp.status_code < 400,
            status=resp.status_code,
            elapsed_ms=elapsed,
        )
    except Exception as exc:
        elapsed = int((time.monotonic() - t0) * 1000)
        return CheckResult(cinema="", endpoint=url, ok=False, status=None, elapsed_ms=elapsed, error=str(exc))


def _request_with_retries(method: str, url: str, **kwargs) -> CheckResult:
    """Ripete la richiesta solo per gli errori di rete (transienti: SSL, DNS, timeout).

    Le stesse condizioni dei connettori, che usano retry e backoff di produzione:
    un errore transitorio che lo scrape assorbe non deve far urlare il healthcheck.
    Gli status HTTP non si ritentano: un 404 o un 500 sono un fatto da riportare.
    """
    last: CheckResult | None = None
    for attempt in range(1, REQUEST_RETRY + 1):
        result = _attempt_request(method, url, **kwargs)
        is_network_error = result.status is None and result.error is not None
        if not is_network_error:
            return result
        last = result
        if attempt < REQUEST_RETRY:
            time.sleep(RETRY_BACKOFF**attempt)
    return last


def _get(cinema: str, url: str, **kwargs) -> CheckResult:
    result = _request_with_retries("get", url, **kwargs)
    return replace(result, cinema=cinema)


def _post(cinema: str, url: str, **kwargs) -> CheckResult:
    result = _request_with_retries("post", url, headers={"Accept": "application/json"}, **kwargs)
    return replace(result, cinema=cinema)


def run_checks() -> list[CheckResult]:
    """Esegue un ping su ogni fonte primaria dei connettori. Nessun parsing, solo status HTTP."""
    today = date.today().isoformat()
    return [
        # --- connettori storici (UA browser-like) ---
        _get("PostModernissimo", POSTMOD_CINEMA_URL),
        _post("The Space (auth)", THE_SPACE_AUTH_URL, json={}),
        _get("UCI", UCI_PROGRAMMING_URL.format(date=today)),
        # --- connettori schema.org (homepage, un'unica richiesta) ---
        _get("Cinema Zenith", CINEMA_ZENITH_URL),
        _get("Nuovo Cinema Castello", NUOVO_CASTELLO_URL),
        _get("Cinema Teatro Concordia", CONCORDIA_URL),
        _get("Cinema Metropolis", METROPOLIS_URL),
        # --- The Space Terni: l'id venue si risolve da qui (il token è già coperto sopra) ---
        _get("The Space Terni (venue)", THE_SPACE_CINEMAS_URL),
    ]


def has_failures(results: list[CheckResult]) -> bool:
    """True se almeno un controllo è fallito: decide l'exit code per cron / Uptime Kuma."""
    return any(not r.ok for r in results)


def print_report(results: list[CheckResult]) -> None:
    print(f"\n{'Cinema':<25} {'Status':>6}  {'Time':>7}  Result")
    print("-" * 60)
    for r in results:
        status_str = str(r.status) if r.status else "ERR"
        mark = "OK" if r.ok else "FAIL"
        print(f"{r.cinema:<25} {status_str:>6}  {r.elapsed_ms:>5}ms  {mark}")
        if r.error:
            print(f"  {'':25} {r.error}")
    print()


if __name__ == "__main__":
    results = run_checks()
    print_report(results)
    if has_failures(results):
        print("One or more endpoints are down.")
        sys.exit(1)
    print("All endpoints OK.")
