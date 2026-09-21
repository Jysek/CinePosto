import { cinemaInitials } from '../constants/cinemas';
import Colors from '../constants/colors';

// Genera l'HTML della mappa (OpenFreeMap + MapLibre GL JS) con i marker dei cinema.
// Usato sia dalla WebView nativa che dall'iframe sul web: è una pagina isolata, quindi
// tutto ciò che serve (CSS e script) deve stare dentro questa stringa.
//
// Perché la versione è pinnata: il bundle arriva da CDN, e un aggiornamento maggiore
// non deve cambiare la mappa sotto i piedi. La 5 è l'ultima con bundle UMD caricabile
// da <script src> e con fallback WebGL1 (la 6 è ESM-only e pretende WebGL2); è anche
// la versione documentata dalla quick start di OpenFreeMap.
const MAPLIBRE_VERSION = '5.24.0';
const MAPLIBRE_CDN = `https://unpkg.com/maplibre-gl@${MAPLIBRE_VERSION}/dist`;

// Stile "liberty": chiaro e colorato, il più vicino al Voyager di CARTO che sostituisce.
// L'attribuzione obbligatoria (OpenFreeMap / OpenMapTiles / OpenStreetMap) arriva da qui.
const STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty';

// Geometria e inquadratura: valori nominati, niente numeri sparsi nell'HTML.
const MARKER_SIZE_PX = 44;
const MARKER_BORDER_PX = 3;
const POPUP_OFFSET_PX = 26;
const FIT_BOUNDS_PADDING_PX = 40;
// MapLibre usa [longitudine, latitudine] (l'opposto di Leaflet): centro sull'Umbria.
const UMBRIA_CENTER = [12.33, 43.105];
const UMBRIA_ZOOM = 10;

// Testi del fallback senza WebGL: stesso tono dello stato di errore di LocationTab.
const FALLBACK_ICON = '⚠️';
const FALLBACK_TITLE = 'Mappa non disponibile';
const FALLBACK_HINT = "Questo dispositivo non supporta la grafica della mappa: usa l'elenco dei cinema qui sotto.";

export default function buildMapHtml(cinemas) {
  const markers = cinemas.map((c) => ({
    slug: c.slug,
    name: c.name,
    address: c.address,
    color: c.color,
    logo: c.logoDataUri,
    initials: cinemaInitials(c.name),
    lat: c.coords.latitude,
    lon: c.coords.longitude,
  }));

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <link rel="stylesheet" href="${MAPLIBRE_CDN}/maplibre-gl.css" />
  <script src="${MAPLIBRE_CDN}/maplibre-gl.js"></script>
  <style>
    html, body { margin: 0; padding: 0; height: 100%; }
    #map { width: 100%; height: 100vh; }

    /* Marker: cerchio con bordo del colore del cinema, dentro il logo (o le iniziali).
       I marker sono elementi DOM sopra il canvas, quindi i data URI dei loghi si
       vedono senza passare per le texture WebGL. */
    .cinema-marker {
      width: ${MARKER_SIZE_PX}px;
      height: ${MARKER_SIZE_PX}px;
      border-radius: 50%;
      overflow: hidden;
      background: #ffffff;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
    }
    .cinema-marker img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .cinema-initials {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: sans-serif;
      font-weight: 700;
      font-size: 15px;
    }

    /* Fallback senza WebGL: stesso tema scuro dell'app (constants/colors.js). */
    .map-fallback {
      height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 24px;
      text-align: center;
      background: ${Colors.background};
    }
    .map-fallback-icon { font-size: 48px; }
    .map-fallback-title { color: ${Colors.white}; font: 700 16px sans-serif; }
    .map-fallback-hint { color: ${Colors.lightGray}; font: 400 14px sans-serif; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    (function () {
      var cinemas = ${JSON.stringify(markers)};

      var MARKER_BORDER = ${MARKER_BORDER_PX};
      var POPUP_OFFSET = ${POPUP_OFFSET_PX};
      var FIT_PADDING = ${FIT_BOUNDS_PADDING_PX};
      var CENTER = ${JSON.stringify(UMBRIA_CENTER)};
      var ZOOM = ${UMBRIA_ZOOM};
      var FALLBACK_ICON = ${JSON.stringify(FALLBACK_ICON)};
      var FALLBACK_TITLE = ${JSON.stringify(FALLBACK_TITLE)};
      var FALLBACK_HINT = ${JSON.stringify(FALLBACK_HINT)};

      // Senza WebGL MapLibre non può disegnare: al posto della mappa si mostra un
      // avviso coerente col tema dell'app. L'elenco dei cinema resta sotto, in schermata.
      function showFallback() {
        var host = document.getElementById('map');
        while (host.firstChild) host.removeChild(host.firstChild);
        host.className = 'map-fallback';

        var icon = document.createElement('div');
        icon.className = 'map-fallback-icon';
        icon.textContent = FALLBACK_ICON;

        var title = document.createElement('div');
        title.className = 'map-fallback-title';
        title.textContent = FALLBACK_TITLE;

        var hint = document.createElement('div');
        hint.className = 'map-fallback-hint';
        hint.textContent = FALLBACK_HINT;

        host.appendChild(icon);
        host.appendChild(title);
        host.appendChild(hint);
      }

      // Logo del cinema se disponibile, altrimenti le iniziali nel colore del cinema,
      // dentro lo stesso cerchio con bordo (nessun pin rotto). Il testo arriva dall'API:
      // lo si scrive con textContent, mai interpretato come markup.
      function createMarkerElement(cinema) {
        var el = document.createElement('div');
        el.className = 'cinema-marker';
        el.style.border = MARKER_BORDER + 'px solid ' + cinema.color;
        el.setAttribute('role', 'img');
        el.setAttribute('aria-label', cinema.name);

        if (cinema.logo) {
          var img = document.createElement('img');
          img.src = cinema.logo;
          img.alt = '';
          el.appendChild(img);
        } else {
          var initials = document.createElement('div');
          initials.className = 'cinema-initials';
          initials.style.color = cinema.color;
          initials.textContent = cinema.initials;
          el.appendChild(initials);
        }
        return el;
      }

      function createPopup(cinema) {
        var content = document.createElement('div');
        var name = document.createElement('strong');
        name.textContent = cinema.name;
        var address = document.createElement('div');
        address.textContent = cinema.address;
        content.appendChild(name);
        content.appendChild(address);
        return new maplibregl.Popup({ offset: POPUP_OFFSET }).setDOMContent(content);
      }

      var map;
      try {
        map = new maplibregl.Map({
          container: 'map',
          style: ${JSON.stringify(STYLE_URL)},
          center: CENTER,
          zoom: ZOOM,
          // Attribuzione sempre visibile e senza prefisso "MapLibre", come la versione
          // Leaflet nascondeva il link "Leaflet": il credito obbligatorio resta.
          attributionControl: { compact: false, customAttribution: '' },
          // La mappa resta 2D come prima: niente rotazione né inclinazione involontarie.
          dragRotate: false,
          pitchWithRotate: false,
          touchPitch: false
        });
      } catch (error) {
        // MapLibre lancia in modo sincrono se non riesce a creare il contesto WebGL.
        showFallback();
        return;
      }

      // Pinch per lo zoom, ma niente rotazione a due dita (Leaflet non ruotava).
      map.touchZoomRotate.disableRotation();

      // Gli errori dopo l'avvio (per esempio una tile non scaricata) non devono
      // sostituire la mappa: si registrano soltanto, per la diagnostica.
      map.on('error', function (event) {
        console.error('Errore mappa:', event && event.error ? event.error : event);
      });

      cinemas.forEach(function (cinema) {
        // Attenzione: MapLibre vuole [longitudine, latitudine].
        new maplibregl.Marker({ element: createMarkerElement(cinema) })
          .setLngLat([cinema.lon, cinema.lat])
          .setPopup(createPopup(cinema))
          .addTo(map);
      });

      if (cinemas.length > 0) {
        var bounds = new maplibregl.LngLatBounds();
        cinemas.forEach(function (cinema) {
          bounds.extend([cinema.lon, cinema.lat]);
        });
        // fitBounds solo a stile caricato: prima il canvas non ha dimensioni.
        map.on('load', function () {
          map.fitBounds(bounds, { padding: FIT_PADDING, duration: 0 });
        });
      }

      // Se la WebView cambia dimensione (rotazione, tastiera) il canvas va riallineato.
      window.addEventListener('resize', function () {
        map.resize();
      });
    })();
  </script>
</body>
</html>`;
}
