// Schermata "Località": mappa Leaflet dei cinema + elenco con indirizzi,
// ognuno apribile in Google Maps. I cinema arrivano dall'API.
import React, { useState, useEffect } from 'react';
import { View, Text, Image, StyleSheet, StatusBar, Linking, TouchableOpacity, Platform, ActivityIndicator, ScrollView } from 'react-native';
import Ionicons from '@react-native-vector-icons/ionicons';
import { Asset } from 'expo-asset';
import CinemaMap from '../components/CinemaMap';
import Colors from '../constants/colors';
import { CINEMA_LOGOS, cinemaColor } from '../constants/cinemas';
import { getCinemas } from '../api/api';

// Converte il logo in data URI per incorporarlo nell'HTML della mappa.
// Usa fetch + FileReader (funzionano su iOS, Android e web) invece di
// expo-file-system, le cui funzioni legacy non esistono più in SDK 54.
// Il FileReader imposta da solo il MIME type corretto.
async function assetToDataUri(assetModule) {
  const asset = Asset.fromModule(assetModule);
  await asset.downloadAsync().catch(() => {});
  const uri = asset.localUri || asset.uri;
  try {
    const blob = await (await fetch(uri)).blob();
    return await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  } catch {
    return uri;
  }
}

export default function LocationTab() {
  const [cinemas, setCinemas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setError(null);
        const data = await getCinemas();
        // Arricchisce ogni cinema con la presentazione (colore/logo) e con il
        // logo convertito in data URI per la mappa; i dati anagrafici restano
        // quelli dell'API (lat/lon piatti).
        const enriched = await Promise.all(
          data.map(async (c) => {
            const logo = CINEMA_LOGOS[c.slug];
            return {
              ...c,
              color: cinemaColor(c.slug),
              logoDataUri: logo ? await assetToDataUri(logo) : null,
            };
          })
        );
        setCinemas(enriched);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const openInMaps = (cinema) => {
    const url = `https://www.google.com/maps/search/?api=1&query=${cinema.lat},${cinema.lon}`;
    Linking.openURL(url);
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorIcon}>⚠️</Text>
        <Text style={styles.errorTitle}>Errore di connessione</Text>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  // La mappa si aspetta `coords.latitude/longitude`: l'API fornisce lat/lon.
  const mapCinemas = cinemas.map((c) => ({
    ...c,
    coords: { latitude: c.lat, longitude: c.lon },
  }));

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <View style={styles.header}>
        <Image source={require('../../assets/logo.png')} style={styles.logo} resizeMode="contain" />
      </View>
      {cinemas.length > 0 && <CinemaMap cinemas={mapCinemas} style={styles.map} />}

      <View style={styles.listPanel}>
        <Text style={styles.panelTitle}>Cinema in Umbria</Text>
        {cinemas.length === 0 ? (
          <Text style={styles.emptyText}>Nessun cinema disponibile</Text>
        ) : (
          // Con 8 cinema l'elenco non entra tutto: scorre, così la mappa resta
          // visibile invece di essere schiacciata a zero.
          <ScrollView showsVerticalScrollIndicator={false}>
            {cinemas.map((cinema) => (
              <TouchableOpacity
                key={cinema.slug}
                style={styles.cinemaRow}
                onPress={() => openInMaps(cinema)}
                activeOpacity={0.7}
              >
                <View style={[styles.dot, { backgroundColor: cinema.color }]} />
                <View style={styles.cinemaDetails}>
                  <Text style={styles.cinemaName}>{cinema.name}</Text>
                  <Text style={styles.cinemaAddress}>{cinema.address}</Text>
                </View>
                <Ionicons name="navigate-outline" size={20} color={Colors.primary} />
              </TouchableOpacity>
            ))}
          </ScrollView>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  centered: {
    flex: 1,
    backgroundColor: Colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  errorIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  errorTitle: {
    color: Colors.white,
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  errorText: {
    color: Colors.lightGray,
    fontSize: 14,
    textAlign: 'center',
  },
  header: {
    alignItems: 'center',
    justifyContent: 'center',
    // Sul telefono i 50px evitano il notch; sul web non servono.
    marginTop: Platform.OS === 'web' ? 16 : 50,
    marginBottom: 8,
  },
  logo: {
    width: 230,
    height: 74,
  },
  map: {
    flex: 1,
  },
  listPanel: {
    backgroundColor: Colors.surface,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    paddingBottom: 32,
    // L'elenco dei cinema non copre mai la mappa: oltre questa quota scorre.
    maxHeight: '55%',
  },
  panelTitle: {
    color: Colors.white,
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  cinemaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.card,
  },
  dot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 12,
  },
  cinemaDetails: {
    flex: 1,
  },
  cinemaName: {
    color: Colors.white,
    fontSize: 15,
    fontWeight: '600',
    marginBottom: 2,
  },
  cinemaAddress: {
    color: Colors.gray,
    fontSize: 12,
  },
  emptyText: {
    color: Colors.gray,
    fontSize: 14,
    textAlign: 'center',
    paddingVertical: 12,
  },
});
