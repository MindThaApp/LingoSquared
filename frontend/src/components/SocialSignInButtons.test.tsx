import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@lingo/shared/api/client";

const renderGoogleButton = vi.fn();
const signInWithApple = vi.fn();

vi.mock("../lib/socialSignIn", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/socialSignIn")>();
  return {
    ...actual,
    renderGoogleButton: (...args: unknown[]) => renderGoogleButton(...args),
    signInWithApple: (...args: unknown[]) => signInWithApple(...args),
  };
});

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: "en" } }),
}));

import { SocialSignInButtons } from "./SocialSignInButtons";
import { socialConfig } from "../lib/socialSignIn";

const apple = { clientId: "com.example.web", redirectUri: "https://example.com/auth/apple" };

describe("SocialSignInButtons", () => {
  beforeEach(() => {
    renderGoogleButton.mockReset().mockResolvedValue(undefined);
    signInWithApple.mockReset();
  });

  it("renders nothing when no provider is configured", () => {
    const { container } = render(
      <SocialSignInButtons onCredential={vi.fn()} config={{ google: null, apple: null }} />,
    );
    expect(container).toBeEmptyDOMElement();
    expect(renderGoogleButton).not.toHaveBeenCalled();
  });

  it("renders Google's button only when Google is configured", async () => {
    render(
      <SocialSignInButtons
        onCredential={vi.fn()}
        config={{ google: { clientId: "google-client" }, apple: null }}
      />,
    );
    expect(screen.getByTestId("google-sign-in")).toBeInTheDocument();
    expect(screen.queryByText("social.continue_with_apple")).not.toBeInTheDocument();
    await waitFor(() => expect(renderGoogleButton).toHaveBeenCalled());
    expect(renderGoogleButton.mock.calls[0][1]).toBe("google-client");
  });

  it("passes a Google credential through", async () => {
    const onCredential = vi.fn().mockResolvedValue(undefined);
    render(
      <SocialSignInButtons
        onCredential={onCredential}
        config={{ google: { clientId: "google-client" }, apple: null }}
      />,
    );
    await waitFor(() => expect(renderGoogleButton).toHaveBeenCalled());
    const options = renderGoogleButton.mock.calls[0][2] as {
      onCredential: (c: unknown) => void;
    };
    const credential = { provider: "google", idToken: "id-token", nonce: "raw" };
    await act(async () => options.onCredential(credential));
    expect(onCredential).toHaveBeenCalledWith(credential);
  });

  it("runs the Apple flow and hands the credential over", async () => {
    const credential = { provider: "apple", idToken: "apple-token", nonce: "raw", displayName: "Jo" };
    signInWithApple.mockResolvedValue(credential);
    const onCredential = vi.fn().mockResolvedValue(undefined);
    render(<SocialSignInButtons onCredential={onCredential} config={{ google: null, apple }} />);

    fireEvent.click(screen.getByRole("button", { name: "social.continue_with_apple" }));

    await waitFor(() => expect(onCredential).toHaveBeenCalledWith(credential));
    expect(signInWithApple).toHaveBeenCalledWith(apple.clientId, apple.redirectUri);
  });

  it("shows the server's error message when sign-in is refused", async () => {
    signInWithApple.mockResolvedValue({ provider: "apple", idToken: "t", nonce: "raw" });
    const onCredential = vi
      .fn()
      .mockRejectedValue(new ApiError(409, "email_exists", "An account with this email already exists."));
    render(<SocialSignInButtons onCredential={onCredential} config={{ google: null, apple }} />);

    fireEvent.click(screen.getByRole("button", { name: "social.continue_with_apple" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("An account with this email already exists.");
  });

  it("stays quiet when the user closes the Apple popup", async () => {
    signInWithApple.mockRejectedValue({ error: "popup_closed_by_user" });
    const onCredential = vi.fn();
    render(<SocialSignInButtons onCredential={onCredential} config={{ google: null, apple }} />);

    fireEvent.click(screen.getByRole("button", { name: "social.continue_with_apple" }));

    await waitFor(() => expect(signInWithApple).toHaveBeenCalled());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(onCredential).not.toHaveBeenCalled();
  });
});

describe("socialConfig", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("is off by default", () => {
    vi.stubEnv("VITE_GOOGLE_CLIENT_ID", "");
    vi.stubEnv("VITE_APPLE_CLIENT_ID", "");
    vi.stubEnv("VITE_APPLE_REDIRECT_URI", "");
    expect(socialConfig()).toEqual({ google: null, apple: null });
  });

  it("needs both Apple values before enabling Apple", () => {
    vi.stubEnv("VITE_GOOGLE_CLIENT_ID", " google-client ");
    vi.stubEnv("VITE_APPLE_CLIENT_ID", "com.example.web");
    vi.stubEnv("VITE_APPLE_REDIRECT_URI", "");
    expect(socialConfig()).toEqual({ google: { clientId: "google-client" }, apple: null });
    vi.stubEnv("VITE_APPLE_REDIRECT_URI", "https://example.com/auth/apple");
    expect(socialConfig().apple).toEqual(apple);
  });
});
