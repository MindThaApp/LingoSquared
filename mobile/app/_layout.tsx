import { Stack } from "expo-router";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { configureApi } from "@lingo/shared/api/client";

import { AuthProvider, useAuth } from "../lib/auth";
import { tokenStorage } from "../lib/tokenStorage";

// configureApi() must run before any API request anywhere in the app (see
// client.ts's platform-seam comment). Module scope of the root layout is the
// earliest point in an expo-router app -- every route module renders under
// this layout, and requests only fire from event handlers/effects long after
// bundle evaluation.
//
// EXPO_PUBLIC_API_BASE_URL is inlined at bundle time (Expo's public-env
// convention, the counterpart of the web app's VITE_API_BASE_URL). The
// localhost fallback matches the dev backend from an iOS simulator; a real
// device or Android emulator needs the env var set to the host machine's
// LAN address (Android's emulator loopback is 10.0.2.2, and "localhost" on
// any physical device is the phone itself).
const apiBaseUrl =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8010";
configureApi({
  baseUrl: apiBaseUrl,
  // Same single-backend simplification as the web app's default: feedback
  // goes to the app backend unless a dedicated central collector URL is
  // baked into the build (see client.ts's feedbackBaseUrl comment).
  feedbackBaseUrl:
    process.env.EXPO_PUBLIC_FEEDBACK_API_URL ?? apiBaseUrl,
  tokenStorage,
});

function RootNavigator() {
  const { status } = useAuth();

  // Hold navigation until the launch-time session check resolves, so the
  // guard below never flashes login for an already-signed-in user (or vice
  // versa).
  if (status === "loading") {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  const signedIn = status === "signedIn";
  return (
    <Stack>
      <Stack.Protected guard={signedIn}>
        <Stack.Screen name="index" options={{ title: "Auvel" }} />
      </Stack.Protected>
      <Stack.Protected guard={!signedIn}>
        <Stack.Screen name="(auth)" options={{ headerShown: false }} />
      </Stack.Protected>
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <RootNavigator />
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#fff",
  },
});
