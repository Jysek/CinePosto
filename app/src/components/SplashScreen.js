// Splash screen d'avvio: animazione del logo (zoom-in, pausa, zoom-out + fade).
import React, { useEffect, useRef } from 'react';
import { Animated, Image, Platform, StyleSheet } from 'react-native';
import Colors from '../constants/colors';

// react-native-web non ha il modulo nativo di animazione: con `true` su web parte
// un warning e l'animazione ripiega comunque sul thread JS. Su iOS/Android resta
// `true`: l'animazione gira sul thread nativo, più fluida.
// ATTENZIONE: tutte le animazioni qui sotto devono usare questa stessa costante;
// mescolare driver JS e nativo sulla stessa Animated.Value rompe a runtime.
const USE_NATIVE_DRIVER = Platform.OS !== 'web';

export default function SplashScreen({ onAnimationEnd }) {
  const scale = useRef(new Animated.Value(0.3)).current;
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.sequence([
      // Zoom in
      Animated.parallel([
        Animated.spring(scale, {
          toValue: 1,
          tension: 40,
          friction: 7,
          useNativeDriver: USE_NATIVE_DRIVER,
        }),
        Animated.timing(opacity, {
          toValue: 1,
          duration: 500,
          useNativeDriver: USE_NATIVE_DRIVER,
        }),
      ]),
      // Pausa
      Animated.delay(1200),
      // Zoom out + fade out
      Animated.parallel([
        Animated.timing(scale, {
          toValue: 1.5,
          duration: 500,
          useNativeDriver: USE_NATIVE_DRIVER,
        }),
        Animated.timing(opacity, {
          toValue: 0,
          duration: 500,
          useNativeDriver: USE_NATIVE_DRIVER,
        }),
      ]),
    ]).start(() => onAnimationEnd());
  }, []);

  return (
    <Animated.View style={[styles.container, { opacity }]}>
      <Animated.Image
        source={require('../../assets/logo.png')}
        style={[styles.logo, { transform: [{ scale }] }]}
        resizeMode="contain"
      />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logo: {
    width: 240,
    height: 80,
  },
});
