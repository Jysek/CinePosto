// Presentazione dei cinema: colori e loghi non sono dati di dominio (nome,
// indirizzo e coordinate arrivano dall'API via `getCinemas()`), ma scelte
// grafiche, quindi vivono qui.
//
// Nota sui loghi: sono inclusi solo i 3 marchi pre-esistenti. Per gli altri
// cinema la UI mostra le iniziali nello stesso slot grafico, così non
// ridistribuiamo marchi di terzi per cui non abbiamo un permesso scritto.

const SPACE_LOGO = require('../../assets/the-space.jpg');
const UCI_LOGO = require('../../assets/uci.png');
const POST_LOGO = require('../../assets/post.jpg');

// Mappa slug -> presentazione. `color` è usato da mappa, elenco e dettaglio;
// `logo` è opzionale (solo i marchi che possiamo mostrare).
const CINEMA_PRESENTATION = {
  'the-space-corciano': { color: '#1E90FF', logo: SPACE_LOGO },
  'uci-perugia': { color: '#FFA500', logo: UCI_LOGO },
  postmodernissimo: { color: '#E50914', logo: POST_LOGO },
  'the-space-terni': { color: '#1E90FF' },
  'cinema-zenith': { color: '#FFA500' },
  'nuovo-cinema-castello': { color: '#1E90FF' },
  'cinema-teatro-concordia': { color: '#FFA500' },
  'cinema-metropolis': { color: '#E50914' },
};

// Palette dei 3 colori storici, riusata per generare un colore stabile
// dagli slug non mappati: un cinema nuovo resta distinguibile senza config.
const FALLBACK_COLORS = ['#1E90FF', '#FFA500', '#E50914'];

// Hash semplice e deterministico: lo stesso slug ottiene sempre lo stesso
// colore, in ogni schermata e a ogni avvio.
function hashSlug(slug) {
  let hash = 0;
  for (let i = 0; i < slug.length; i += 1) {
    hash = (hash * 31 + slug.charCodeAt(i)) % 100000;
  }
  return hash;
}

// Colore di presentazione: quello mappato, o uno deterministico dalla palette.
export function cinemaColor(slug) {
  if (!slug) return FALLBACK_COLORS[0];
  const mapped = CINEMA_PRESENTATION[slug]?.color;
  return mapped || FALLBACK_COLORS[hashSlug(slug) % FALLBACK_COLORS.length];
}

// Iniziali (max 2 lettere) usate al posto del logo quando questo manca.
export function cinemaInitials(name) {
  const words = (name || '').trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return '?';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

// Solo i cinema con un marchio disponibile (gli altri usano le iniziali).
export const CINEMA_LOGOS = Object.fromEntries(
  Object.entries(CINEMA_PRESENTATION)
    .filter(([, presentation]) => presentation.logo)
    .map(([slug, presentation]) => [slug, presentation.logo])
);
