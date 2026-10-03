// Helper condiviso per la URL di Google Maps di un cinema.
// Unica fonte della URL: la usa la schermata Località (elenco) e la erediterà
// il popup della mappa (fase-18). Il dato anagrafico arriva dall'API: qui non
// ci sono URL hardcoded per cinema.
import { Linking } from 'react-native';

// URL a coordinate: il fallback quando il cinema non ha la place URL.
// Non è una scheda del luogo: Maps la mostra come pin di coordinate in cui il
// titolo sono le stesse coordinate, quindi deve restare solo di riserva.
const COORDS_PLACEHOLDER_URL = 'https://www.google.com/maps/search/?api=1&query=';

/**
 * URL di Google Maps da aprire per un cinema dell'API.
 *
 * Se il backend fornisce `maps_place_url` (place URL del luogo salvato: nome,
 * foto, recensioni, orari) quella è la URL giusta. Altrimenti si cade indietro
 * alla ricerca a coordinate, che funziona sempre ma apre il pin senza scheda.
 *
 * @param {object} cinema - cinema dall'API (forma `Cinema` in docs/backend/api.md:
 *   slug, name, lat, lon, maps_place_url, …)
 * @returns {string} URL da passare a Linking.openURL
 */
export function cinemaMapsUrl(cinema) {
  if (cinema && cinema.maps_place_url) {
    return cinema.maps_place_url;
  }
  return `${COORDS_PLACEHOLDER_URL}${cinema ? cinema.lat : ''},${cinema ? cinema.lon : ''}`;
}

/**
 * Apre la URL del cinema nel browser / app Maps del sistema operativo.
 */
export function openCinemaInMaps(cinema) {
  return Linking.openURL(cinemaMapsUrl(cinema));
}
