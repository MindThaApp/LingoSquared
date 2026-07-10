import { StatusBar } from "expo-status-bar";
import { StyleSheet, Text, View } from "react-native";

import { configureApi } from "@lingo/shared/api/client";
import type { CourseSummary } from "@lingo/shared/api/types";

// Phase 0 proof-of-concept only: this is the single most important check in
// the whole mobile scaffold. @lingo/shared ships raw TypeScript source (no
// build step -- see packages/shared/package.json's own comment) and is
// resolved via its package.json "exports" map. Metro's module resolution is
// genuinely different from Vite's (which frontend/ already proved works);
// confirming BOTH a type-only import (CourseSummary, erased at compile time)
// AND a real runtime import (configureApi, actually called below) resolve
// correctly through Metro + the npm-workspaces symlink + metro.config.js's
// monorepo watchFolders is what this screen exists to demonstrate.
configureApi({
  baseUrl: "http://localhost:8010",
  feedbackBaseUrl: "http://localhost:8010",
  tokenStorage: {
    get: () => null,
    set: () => {},
    clear: () => {},
  },
});

// Never actually constructed -- exists purely so CourseSummary above is a
// real, used type reference (not an unused import a stricter lint config
// might flag) and so its field names render on screen as visible proof the
// type came through intact.
const dummyCourse: CourseSummary = {
  id: "phase-0-dummy",
  source_language: "en",
  target_language: "nl",
  title: "Phase 0 dummy course",
  level: "A1",
  unit_count: 0,
};

export default function Index() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Lingo² Mobile — Phase 0</Text>
      <Text style={styles.subtitle}>
        @lingo/shared resolved through Metro: {dummyCourse.title} (
        {dummyCourse.source_language} → {dummyCourse.target_language})
      </Text>
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
});
