import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const socialConfigEndpoint = vi.fn();

vi.mock("@lingo/shared/api/endpoints", () => ({
  AuthApi: { socialConfig: () => socialConfigEndpoint() },
}));

import {
  loadServerProviders,
  resetServerProvidersForTests,
  restrictToServer,
  useSocialConfig,
} from "./useSocialConfig";

const google = { clientId: "google-client" };
const apple = { clientId: "com.example.web", redirectUri: "https://example.com/auth/apple" };

function stubBuild() {
  vi.stubEnv("VITE_GOOGLE_CLIENT_ID", google.clientId);
  vi.stubEnv("VITE_APPLE_CLIENT_ID", apple.clientId);
  vi.stubEnv("VITE_APPLE_REDIRECT_URI", apple.redirectUri);
}

describe("restrictToServer", () => {
  it("keeps only the providers the backend accepts", () => {
    expect(restrictToServer({ google, apple }, ["apple"])).toEqual({ google: null, apple });
    expect(restrictToServer({ google, apple }, [])).toEqual({ google: null, apple: null });
  });

  it("never adds a provider the build lacks", () => {
    expect(restrictToServer({ google, apple: null }, ["google", "apple"])).toEqual({ google, apple: null });
  });
});

describe("useSocialConfig", () => {
  beforeEach(() => {
    resetServerProvidersForTests();
    socialConfigEndpoint.mockReset();
  });
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("offers nothing while the backend switch is off, even with client IDs set", async () => {
    stubBuild();
    socialConfigEndpoint.mockResolvedValue({ providers: [] });
    const { result } = renderHook(() => useSocialConfig());
    await waitFor(() => expect(socialConfigEndpoint).toHaveBeenCalled());
    expect(result.current).toEqual({ google: null, apple: null });
  });

  it("offers what both the build and the backend allow", async () => {
    stubBuild();
    socialConfigEndpoint.mockResolvedValue({ providers: ["google"] });
    const { result } = renderHook(() => useSocialConfig());
    await waitFor(() => expect(result.current.google).toEqual(google));
    expect(result.current.apple).toBeNull();
  });

  it("does not ask the backend when the build has no provider", () => {
    vi.stubEnv("VITE_GOOGLE_CLIENT_ID", "");
    vi.stubEnv("VITE_APPLE_CLIENT_ID", "");
    vi.stubEnv("VITE_APPLE_REDIRECT_URI", "");
    const { result } = renderHook(() => useSocialConfig());
    expect(result.current).toEqual({ google: null, apple: null });
    expect(socialConfigEndpoint).not.toHaveBeenCalled();
  });

  it("does not ask the backend when skipped", () => {
    stubBuild();
    renderHook(() => useSocialConfig(true));
    expect(socialConfigEndpoint).not.toHaveBeenCalled();
  });
});

describe("loadServerProviders", () => {
  beforeEach(() => {
    resetServerProvidersForTests();
  });

  it("asks once and shares the answer", async () => {
    const fetchConfig = vi.fn().mockResolvedValue({ providers: ["apple"] });
    expect(await loadServerProviders(fetchConfig)).toEqual(["apple"]);
    expect(await loadServerProviders(fetchConfig)).toEqual(["apple"]);
    expect(fetchConfig).toHaveBeenCalledTimes(1);
  });

  it("treats a failed request as no providers and asks again later", async () => {
    const failing = vi.fn().mockRejectedValue(new Error("offline"));
    expect(await loadServerProviders(failing)).toEqual([]);
    const working = vi.fn().mockResolvedValue({ providers: ["google"] });
    expect(await loadServerProviders(working)).toEqual(["google"]);
  });
});
