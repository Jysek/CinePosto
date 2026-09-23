"""Test del healthcheck: copertura delle fonti, gestione degli errori HTTP, exit code.

I test non toccano la rete: le richieste sono mockate con unittest.mock, come in test_http.py.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from unittest.mock import MagicMock, patch

import requests

# import dallo script (non è un package): la path è preparata dallo stesso healthcheck
import healthcheck
from healthcheck import CheckResult, has_failures, run_checks
from scraper.config import (
    CINEMA_ZENITH_URL,
    CONCORDIA_URL,
    METROPOLIS_URL,
    NUOVO_CASTELLO_URL,
    REQUEST_RETRY,
)

# una voce per ogni connettore registrato in scraper/scraper/main.py
EXPECTED_SOURCES = 8


def _mock_response(status_code: int) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    return resp


@contextmanager
def _mocked_requests():
    """Contesto che rende run_checks() offline: nessun test tocca la rete."""
    with ExitStack() as stack:
        stack.enter_context(patch.object(healthcheck.requests, "get", return_value=_mock_response(200)))
        stack.enter_context(patch.object(healthcheck.requests, "post", return_value=_mock_response(200)))
        yield


# --- copertura delle fonti ---


def test_run_checks_covers_every_configured_connector():
    """Il numero di controlli è pari al numero di fonti primarie: se un connettore nuovo
    non viene aggiunto qui, questo test fallisce (era esattamente il difetto originale)."""
    with _mocked_requests():
        assert len(run_checks()) == EXPECTED_SOURCES


def test_all_connector_homepages_are_monitored():
    """Le homepage delle sale schema.org compaiono fra gli endpoint controllati: se una
    costante cambia senza aggiornare l'elenco, il test se ne accorge."""
    with _mocked_requests():
        endpoints = [r.endpoint for r in run_checks()]
    for url in (CINEMA_ZENITH_URL, NUOVO_CASTELLO_URL, CONCORDIA_URL, METROPOLIS_URL):
        assert url in endpoints


# --- gestione degli errori HTTP ---


def _post_returning(status_code: int) -> MagicMock:
    """Il check di auth (POST) non è oggetto di questi test: viene mockato e risponde bene."""
    return _mock_response(status_code)


def test_http_failure_is_reported_as_not_ok():
    """Un errore di connessione persistente diventa un CheckResult non ok, senza
    eccezioni propagate: ogni check GET fallito è stato ritentato REQUEST_RETRY volte."""
    with (
        patch.object(healthcheck.requests, "get", side_effect=requests.ConnectionError("boom")),
        patch.object(healthcheck.requests, "post", return_value=_post_returning(200)),
        patch.object(healthcheck.time, "sleep"),
    ):
        results = run_checks()

    # 7 check GET + 1 POST che risponde bene: tutti i GET falliti, l'auth no
    failed = [r for r in results if r.error is not None]
    assert len(failed) == EXPECTED_SOURCES - 1
    for r in failed:
        assert r.ok is False
        assert r.status is None
        assert "boom" in r.error


def test_persistent_failure_is_retried_with_backoff():
    """Stesso assorbimento dei connettori: le richieste si ripetono REQUEST_RETRY volte
    prima di dichiarare la fonte giù."""
    attempts = []

    def always_fails(url, **kwargs):
        attempts.append(url)
        raise requests.ConnectionError("giù" + str(len(attempts)))

    with (
        patch.object(healthcheck.requests, "get", side_effect=always_fails),
        patch.object(healthcheck.requests, "post", return_value=_post_returning(200)),
        patch.object(healthcheck.time, "sleep"),
    ):
        results = run_checks()

    assert len([r for r in results if r.error is not None]) == EXPECTED_SOURCES - 1
    # REQUEST_RETRY tentativi per ognuna delle 7 fonti GET
    assert len(attempts) == (EXPECTED_SOURCES - 1) * REQUEST_RETRY


def test_transient_network_error_is_absorbed_by_retry():
    """Un errore di rete che al tentativo successivo passa non urla: lo scrape reale
    assorbe questi transienti con retry_request, il check deve comportarsi uguale."""
    state = {"failures_left": 1}

    def fails_then_succeeds(url, **kwargs):
        if state["failures_left"] > 0:
            state["failures_left"] -= 1
            raise requests.ConnectionError("transitorio")
        return _mock_response(200)

    with (
        patch.object(healthcheck.requests, "get", side_effect=fails_then_succeeds),
        patch.object(healthcheck.requests, "post", return_value=_post_returning(200)),
        patch.object(healthcheck.time, "sleep"),
    ):
        results = run_checks()

    assert [r for r in results if r.error is not None] == [], (
        "un transient recuperato dal retry non deve risultare fallito"
    )
    assert all(r.ok for r in results)


def test_non_2xx_status_is_reported_as_not_ok():
    with (
        patch.object(healthcheck.requests, "get", return_value=_mock_response(500)),
        patch.object(healthcheck.requests, "post", return_value=_mock_response(500)),
    ):
        results = run_checks()
    assert all(not r.ok for r in results)
    assert all(r.status == 500 for r in results)


def test_200_is_ok_and_404_is_not_ok():
    """Il contratto è status < 400: un 200 passa, un 404 è una fonte rotta (nessuna tolleranza nuova)."""
    with (
        patch.object(healthcheck.requests, "get", return_value=_mock_response(200)),
        patch.object(healthcheck.requests, "post", return_value=_mock_response(200)),
    ):
        ok_results = run_checks()
    assert all(r.ok for r in ok_results)

    with (
        patch.object(healthcheck.requests, "get", return_value=_mock_response(404)),
        patch.object(healthcheck.requests, "post", return_value=_mock_response(404)),
    ):
        not_ok_results = run_checks()
    assert all(not r.ok for r in not_ok_results)
    assert all(r.status == 404 for r in not_ok_results)


# --- exit code ---


def test_report_returns_exit_code_1_when_a_source_fails():
    """La decisione di exit code è estratta in has_failures e testabile senza avviare il processo."""
    results = [
        CheckResult(cinema="a", endpoint="u", ok=True, status=200, elapsed_ms=1),
        CheckResult(cinema="b", endpoint="u", ok=False, status=None, elapsed_ms=1, error="x"),
    ]
    assert has_failures(results) is True
    assert has_failures([results[0]]) is False
    assert has_failures([]) is False
