// Avviso non bloccante: la programmazione mostrata non è aggiornata.
// Stile allineato alla palette scura dell'app (Colors) e al bottone
// "Riprova" di FilmsTab. Non copre la griglia né sostituisce lo stato
// di errore: i dati vecchi si mostrano, l'avviso li accompagna.
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import Ionicons from '@react-native-vector-icons/ionicons';
import Colors from '../constants/colors';
import { formatDateTime } from '../utils/dates';

export default function StaleDataBanner({ latestScrapedAt, onRetry }) {
  return (
    <View style={styles.banner}>
      <Ionicons name="warning-outline" size={22} color={Colors.primary} style={styles.icon} />
      <View style={styles.textBlock}>
        <Text style={styles.title}>Programmazione non aggiornata</Text>
        <Text style={styles.detail}>
          {latestScrapedAt
            ? `Ultimo aggiornamento: ${formatDateTime(latestScrapedAt)}`
            : 'Nessun dato disponibile.'}
        </Text>
      </View>
      {onRetry && (
        <TouchableOpacity style={styles.retryButton} onPress={onRetry} activeOpacity={0.7}>
          <Ionicons name="refresh" size={16} color={Colors.white} />
          <Text style={styles.retryText}>Riprova</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    // Bordo accentato a sinistra: visibile ma meno aggressivo di un banner pieno.
    borderLeftWidth: 4,
    borderLeftColor: Colors.primary,
    borderRadius: 8,
    marginHorizontal: 16,
    marginBottom: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 10,
  },
  icon: {
    marginTop: 2,
  },
  textBlock: {
    flex: 1,
  },
  title: {
    color: Colors.white,
    fontSize: 14,
    fontWeight: '600',
  },
  detail: {
    color: Colors.lightGray,
    fontSize: 12,
    marginTop: 2,
  },
  // Stesso look del bottone "Riprova" di FilmsTab (retryButton/retryText).
  retryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.primary,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    gap: 6,
  },
  retryText: {
    color: Colors.white,
    fontSize: 13,
    fontWeight: '600',
  },
});
