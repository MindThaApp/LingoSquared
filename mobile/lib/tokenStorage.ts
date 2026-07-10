import * as SecureStore from "expo-secure-store";

import type { ApiTokenStorage } from "@lingo/shared/api/client";

// SecureStore-backed implementation of @lingo/shared's ApiTokenStorage --
// the mobile counterpart of the web app's localStorage-backed one.
// SecureStore is the right home for a bearer token on device (Keychain on
// iOS, EncryptedSharedPreferences/Keystore on Android), unlike a plain
// AsyncStorage value.
//
// ApiTokenStorage is a synchronous interface (client.ts reads the token
// inline on every request). expo-secure-store@57 has synchronous
// getItem()/setItem() but only an async deleteItemAsync() -- so we keep an
// in-memory mirror as the source of truth for reads and treat SecureStore
// as the persistence layer. That makes clear() take effect immediately
// (the next request sends no Authorization header) even though the
// underlying keychain delete completes asynchronously.
const ACCESS_TOKEN_KEY = "lingo.access_token";

// undefined = not read from SecureStore yet; null = known-absent.
let cached: string | null | undefined;

export const tokenStorage: ApiTokenStorage = {
  get: () => {
    if (cached === undefined) {
      try {
        cached = SecureStore.getItem(ACCESS_TOKEN_KEY);
      } catch {
        // SecureStore unavailable (e.g. expo web target) -- degrade to a
        // memory-only session rather than crashing every API call.
        cached = null;
      }
    }
    return cached;
  },
  set: (token: string) => {
    cached = token;
    try {
      SecureStore.setItem(ACCESS_TOKEN_KEY, token);
    } catch {
      // Memory-only fallback, same rationale as get().
    }
  },
  clear: () => {
    cached = null;
    SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY).catch(() => {
      // Best-effort: the in-memory mirror above already guarantees no
      // further request uses the token this session; a leftover keychain
      // row is re-read as a stale token next launch, which AuthApi.me()
      // validation in lib/auth.tsx rejects and clears properly.
    });
  },
};
