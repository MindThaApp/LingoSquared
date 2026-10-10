import { useEffect, useState } from "react";
import { AuthApi } from "@lingo/shared/api/endpoints";
import type { SocialProvider } from "@lingo/shared/api/types";
import { socialConfig, type SocialConfig } from "./socialSignIn";

const NONE: SocialConfig = { google: null, apple: null };

// The build decides which providers this client CAN offer (VITE_* IDs);
// the backend decides which it accepts right now (GET /auth/social/config,
// empty while SOCIAL_SIGN_IN_ENABLED is off). A button shows only when
// both agree, so turning the backend switch off hides the buttons without
// a rebuild.
export function restrictToServer(config: SocialConfig, providers: readonly SocialProvider[]): SocialConfig {
  return {
    google: providers.includes("google") ? config.google : null,
    apple: providers.includes("apple") ? config.apple : null,
  };
}

// One request per page load, shared by every component that asks.
let serverProviders: Promise<SocialProvider[]> | null = null;

export function loadServerProviders(
  fetchConfig: () => Promise<{ providers: SocialProvider[] }> = AuthApi.socialConfig,
): Promise<SocialProvider[]> {
  if (!serverProviders) {
    serverProviders = fetchConfig()
      .then((result) => (Array.isArray(result?.providers) ? result.providers : []))
      .catch(() => {
        // Show nothing now; ask again next time a page needs it.
        serverProviders = null;
        return [];
      });
  }
  return serverProviders;
}

export function resetServerProvidersForTests() {
  serverProviders = null;
}

// The providers to offer: the build's configuration narrowed to what the
// backend accepts. Nothing is offered until the backend has answered, and
// no request is made when the build has no provider at all. Pass
// skip=true when the caller already has a configuration of its own.
export function useSocialConfig(skip = false): SocialConfig {
  const [config, setConfig] = useState<SocialConfig>(NONE);
  useEffect(() => {
    if (skip) return;
    const built = socialConfig();
    if (!built.google && !built.apple) return;
    let cancelled = false;
    void loadServerProviders().then((providers) => {
      if (!cancelled) setConfig(restrictToServer(built, providers));
    });
    return () => {
      cancelled = true;
    };
  }, [skip]);
  return config;
}
