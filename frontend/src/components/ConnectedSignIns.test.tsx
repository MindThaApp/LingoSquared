import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const linkSocial = vi.fn();
const unlinkSocial = vi.fn();
let identities: { provider: "google" | "apple"; created_at: string }[] = [];
let lastOnCredential: ((credential: unknown) => Promise<void>) | null = null;

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({ user: { id: "u1", email: "a@example.com", identities }, linkSocial, unlinkSocial }),
}));
vi.mock("./SocialSignInButtons", () => ({
  SocialSignInButtons: ({ onCredential }: { onCredential: (c: unknown) => Promise<void> }) => {
    lastOnCredential = onCredential;
    return <div data-testid="social-buttons" />;
  },
}));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

import { ConnectedSignIns } from "./ConnectedSignIns";

describe("ConnectedSignIns", () => {
  beforeEach(() => {
    linkSocial.mockReset().mockResolvedValue(undefined);
    unlinkSocial.mockReset().mockResolvedValue(undefined);
    identities = [];
    lastOnCredential = null;
  });

  it("sends the current password along when connecting a provider", async () => {
    render(<ConnectedSignIns />);
    expect(screen.getByText("social.connected_none")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("social.current_password"), { target: { value: "secret-pass" } });
    const credential = { provider: "google", idToken: "t", nonce: "n" };
    await act(async () => lastOnCredential?.(credential));
    expect(linkSocial).toHaveBeenCalledWith(credential, "secret-pass");
  });

  it("disconnects a linked provider with the current password", async () => {
    identities = [{ provider: "google", created_at: "2026-10-10T00:00:00Z" }];
    render(<ConnectedSignIns />);
    fireEvent.change(screen.getByLabelText("social.current_password"), { target: { value: "secret-pass" } });
    fireEvent.click(screen.getByRole("button", { name: "social.disconnect" }));
    await waitFor(() => expect(unlinkSocial).toHaveBeenCalledWith("google", "secret-pass"));
  });
});
