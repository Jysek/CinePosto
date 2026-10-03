import React from 'react';
import { Linking } from 'react-native';
import { WebView } from 'react-native-webview';
import buildMapHtml from './mapHtml';

// Versione NATIVA (iOS/Android) della mappa: usa react-native-webview.
// Sul web Metro carica automaticamente CinemaMap.web.js al suo posto.

// Il popup è un link: dentro la WebView i link non aprono un browser esterno
// da soli, quindi la pagina devolve l'apertura qui via postMessage (vedi
// mapHtml.js) e la eseguiamo con Linking, che passa per l'app Maps del sistema.

// Solo messaggi in HTTPS: la pagina è HTML nostro ma il canale postMessage
// non ha schema, quindi la validazione al confine resta doverosa.
const OPENABLE_URL_PATTERN = /^https:\/\//;

// Tipi di messaggio che la pagina ci può mandare: tutto il resto si ignora.
const MESSAGE_TYPE_OPEN_MAPS = 'openMaps';

function openExternally(url) {
  Linking.openURL(url).catch((error) => {
    // Nessun handler per la URL (per esempio Maps disinstallato su Android):
    // si registra e basta, un crash qui non è giustificato.
    console.warn('Apertura Google Maps fallita:', url, error.message);
  });
}

function handleMessage(event) {
  let message;
  try {
    message = JSON.parse(event.nativeEvent.data);
  } catch (error) {
    console.warn('Messaggio non JSON dalla mappa:', event.nativeEvent.data, error.message);
    return;
  }
  if (!message || message.type !== MESSAGE_TYPE_OPEN_MAPS) {
    console.warn('Messaggio sconosciuto dalla mappa:', message && message.type);
    return;
  }
  if (typeof message.url !== 'string' || !OPENABLE_URL_PATTERN.test(message.url)) {
    console.warn('URL non apribile dal messaggio della mappa:', typeof message.url);
    return;
  }
  openExternally(message.url);
}

export default function CinemaMap({ cinemas, style }) {
  return (
    <WebView
      source={{ html: buildMapHtml(cinemas) }}
      style={style}
      originWhitelist={['*']}
      scrollEnabled={false}
      javaScriptEnabled={true}
      onMessage={handleMessage}
    />
  );
}
