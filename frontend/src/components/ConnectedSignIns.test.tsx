import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@lingo/shared/api/client";

const linkSocial = vi.fn();
const unlinkSocial = vi.fn();
let identities: { provider: "google" | "apple"; created_at: string }[] = [];
let hasPassword: boolean | undefined = true;
let lastOnCredential: ((credential: unknown) => Promise<void>) | null = null;
let lastConfig: unknown = null;

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "u1", email: "a@example.com", identities, has_password: hasPassword },
    linkSocial,
    unlinkSocial,
  }),
}));
vi.mock("./SocialSignInButtons", () => ({
  SocialSignInButtons: ({
    onCredential,
    config,
  }: {
    onCredential: (c: unknown) => Promise<void>;
    config: unknown;
  }) => {
    lastOnCredential = onCredential;
    lastConfig = config;
    return <div data-testid="social-buttons" />;
  },
}));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

import { ConnectedSignIns } from "./ConnectedSignIns";

const google = { clientId: "google-client" };
const apple = { clientId: "com.example.web", redirectUri: "https://example.com/auth/apple" };
const both = { google, apple };

describe("ConnectedSignIns", () => {
  beforeEach(() => {
    linkSocial.mockReset().mockResolvedValue(undefined);
    unlinkSocial.mockReset().mockResolvedValue(undefined);
    identities = [];
    hasPassword = true;
    lastOnCredential = null;
    lastConfig = null;
  });

  it("sends the current password along when connecting a provider", async () => {
    render(<ConnectedSignIns config={both} />);
    expect(screen.getByText("social.connected_none")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("social.current_password"), { target: { value: "secret-pass" } });
    const credential = { provider: "google", idToken: "t", nonce: "n" };
    await act(async () => lastOnCredential?.(credential));
    expect(linkSocial).toHaveBeenCalledWith(credential, "secret-pass");
  });

  it("only offers providers that are not linked yet", () => {
    identities = [{ provider: "google", created_at: "2026-10-10T00:00:00Z" }];
    render(<ConnectedSignIns config={both} />);
    expect(lastConfig).toEqual({ google: null, apple });
  });

  it("disconnects a linked provider with the current password", async () => {
    identities = [{ provider: "google", created_at: "2026-10-10T00:00:00Z" }];
    render(<ConnectedSignIns config={both} />);
    fireEvent.change(screen.getByLabelText("social.current_password"), { target: { value: "secret-pass" } });
    fireEvent.click(screen.getByRole("button", { name: "social.disconnect" }));
    await waitFor(() => expect(unlinkSocial).toHaveBeenCalledWith("google", "secret-pass"));
  });

  it("retries a sign-in refused for a wrong password without a new popup", async () => {
    linkSocial.mockRejectedValueOnce(
      new ApiError(403, "reauthentication_required", "Enter your current password to change linked sign-ins."),
    );
    render(<ConnectedSignIns config={both} />);
    fireEvent.change(screen.getByLabelText("social.current_password"), { target: { value: "typo" } });
    const credential = { provider: "google", idToken: "t", nonce: "n" };
    await act(async () => {
      await lastOnCredential?.(credential).catch(() => undefined);
    });

    fireEvent.change(screen.getByLabelText("social.current_password"), { target: { value: "secret-pass" } });
    fireEvent.click(screen.getByRole("button", { name: "social.retry_link" }));

    await waitFor(() => expect(linkSocial).toHaveBeenLastCalledWith(credential, "secret-pass"));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "social.retry_link" })).not.toBeInTheDocument(),
    );
  });

  it("asks an account without a password to sign in with a linked provider first", async () => {
    hasPassword = false;
    identities = [{ provider: "google", created_at: "2026-10-10T00:00:00Z" }];
    render(<ConnectedSignIns config={both} />);
    expect(screen.queryByLabelText("social.current_password")).not.toBeInTheDocument();
    expect(screen.getByText("social.reauth_title")).toBeInTheDocument();
    // Step 1: only the linked provider is offered, to confirm it's them.
    expect(lastConfig).toEqual({ google, apple: null });
    const reauth = { provider: "google", idToken: "g", nonce: "n1" };
    await act(async () => lastOnCredential?.(reauth));
    expect(linkSocial).not.toHaveBeenCalled();

    // Step 2: the provider to connect.
    expect(screen.getByText("social.reauth_done")).toBeInTheDocument();
    expect(lastConfig).toEqual({ google: null, apple });
    const credential = { provider: "apple", idToken: "a", nonce: "n2" };
    await act(async () => lastOnCredential?.(credential));
    expect(linkSocial).toHaveBeenCalledWith(credential, undefined, reauth);
  });

  it("starts over from the confirmation step when a passwordless link fails", async () => {
    hasPassword = false;
    identities = [{ provider: "google", created_at: "2026-10-10T00:00:00Z" }];
    linkSocial.mockRejectedValueOnce(new ApiError(403, "invalid_credentials", "Invalid social sign-in token"));
    render(<ConnectedSignIns config={both} />);
    await act(async () => lastOnCredential?.({ provider: "google", idToken: "g", nonce: "n1" }));
    await act(async () => lastOnCredential?.({ provider: "apple", idToken: "a", nonce: "n2" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid social sign-in token");
    expect(screen.getByText("social.reauth_title")).toBeInTheDocument();
  });

  it("disconnects without a password when the account has none", async () => {
    hasPassword = false;
    identities = [
      { provider: "google", created_at: "2026-10-10T00:00:00Z" },
      { provider: "apple", created_at: "2026-10-10T00:00:00Z" },
    ];
    render(<ConnectedSignIns config={both} />);
    fireEvent.click(screen.getAllByRole("button", { name: "social.disconnect" })[1]);
    await waitFor(() => expect(unlinkSocial).toHaveBeenCalledWith("apple", undefined));
  });
});
