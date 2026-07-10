import { StatusBar } from "expo-status-bar";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { useAuth } from "../lib/auth";

// Placeholder signed-in home. This screen sits behind the root layout's
// Stack.Protected guard, so rendering at all means a real authenticated
// session exists (validated against GET /auth/me at launch, or freshly
// created by login/register). The Phase 0 @lingo/shared-resolution proof
// that used to live here has served its purpose -- the auth flow now
// exercises the shared client for real.
export default function HomeScreen() {
  const { user, signOut } = useAuth();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>
        Welcome{user?.display_name ? `, ${user.display_name}` : ""}!
      </Text>
      <Text style={styles.subtitle}>
        Signed in as {user?.email ?? "unknown"}. Courses, lessons, and practice
        come next.
      </Text>
      <Pressable
        style={styles.signOutButton}
        onPress={signOut}
        accessibilityRole="button"
      >
        <Text style={styles.signOutText}>Sign out</Text>
      </Pressable>
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    gap: 12,
  },
  title: {
    fontSize: 20,
    fontWeight: "600",
  },
  subtitle: {
    fontSize: 14,
    textAlign: "center",
    color: "#555",
  },
  signOutButton: {
    marginTop: 12,
    borderWidth: 1,
    borderColor: "#b00020",
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  signOutText: {
    color: "#b00020",
    fontSize: 15,
    fontWeight: "600",
  },
});
