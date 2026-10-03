import React from 'react';
import { View } from 'react-native';
import buildMapHtml from './mapHtml';

// Versione WEB della mappa: react-native-webview non esiste nel browser,
// quindi usiamo un normale <iframe> con lo stesso HTML MapLibre.
// Nessun bridge postMessage qui: il popup è un <a target="_blank"> e
// l'iframe apre da solo una nuova scheda (nessun sandbox che lo blocchi).
export default function CinemaMap({ cinemas, style }) {
  return (
    <View style={style}>
      <iframe
        srcDoc={buildMapHtml(cinemas)}
        title="Mappa dei cinema"
        style={{ width: '100%', height: '100%', border: 'none' }}
      />
    </View>
  );
}
