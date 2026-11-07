import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@lingo/shared/api/client";

const requestPasswordReset = vi.fn();
const confirmPasswordReset = vi.fn();
let rejectWith: unknown = null;
vi.mock("@lingo/shared/api/endpoints", () => ({
  AuthApi: {
    requestPasswordReset: async (...a: unknown[]) => {
      requestPasswordReset(...a);
      if (rejectWith) throw rejectWith;
      return { status: "ok" };
    },
    confirmPasswordReset: async (...a: unknown[]) => {
      confirmPasswordReset(...a);
      if (rejectWith) throw rejectWith;
      return {};
    },
  },
}));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

import { ForgotPasswordPage } from "./ForgotPasswordPage";
import { ResetPasswordPage } from "./ResetPasswordPage";

const assign = vi.fn();

beforeEach(() => {
  requestPasswordReset.mockReset();
  confirmPasswordReset.mockReset();
  assign.mockReset();
  rejectWith = null;
  Object.defineProperty(window, "location", { value: { ...window.location, assign }, writable: true });
});

function renderReset(url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <ResetPasswordPage />
    </MemoryRouter>,
  );
}

function fillReset(next: string, repeat: string) {
  fireEvent.change(screen.getByLabelText("reset.new_password"), { target: { value: next } });
  fireEvent.change(screen.getByLabelText("reset.confirm_password"), { target: { value: repeat } });
  fireEvent.submit(screen.getByRole("button", { name: "reset.new_submit" }).closest("form")!);
}

describe("ForgotPasswordPage", () => {
  it("sends the trimmed email and shows the generic confirmation", async () => {
    render(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText("reset.email"), { target: { value: " a@example.com " } });
    fireEvent.submit(screen.getByRole("button", { name: "reset.request_submit" }).closest("form")!);
    await waitFor(() => expect(requestPasswordReset).toHaveBeenCalledWith("a@example.com"));
    expect(await screen.findByText("reset.request_sent")).toBeInTheDocument();
  });

  it("shows the rate-limit message on 429", async () => {
    rejectWith = new ApiError(429, "password_reset_rate_limited", "slow down");
    render(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText("reset.email"), { target: { value: "a@example.com" } });
    fireEvent.submit(screen.getByRole("button", { name: "reset.request_submit" }).closest("form")!);
    expect(await screen.findByRole("alert")).toHaveTextContent("reset.rate_limited");
  });
});

describe("ResetPasswordPage", () => {
  it("submits the token from the URL and reloads at home on success", async () => {
    renderReset("/reset-password?token=abc123");
    fillReset("new-password-1", "new-password-1");
    await waitFor(() => expect(confirmPasswordReset).toHaveBeenCalledWith("abc123", "new-password-1"));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/"));
  });

  it("rejects mismatch and short passwords without calling the API", () => {
    renderReset("/reset-password?token=abc123");
    fillReset("new-password-1", "different-one");
    expect(screen.getByRole("alert")).toHaveTextContent("reset.mismatch");
    fillReset("short", "short");
    expect(screen.getByRole("alert")).toHaveTextContent("reset.too_short");
    expect(confirmPasswordReset).not.toHaveBeenCalled();
  });

  it("shows the invalid-link state with no token, and after an invalid_reset_token error", async () => {
    const first = renderReset("/reset-password");
    expect(screen.getByRole("alert")).toHaveTextContent("reset.invalid_link");
    first.unmount();
    rejectWith = new ApiError(400, "invalid_reset_token", "bad");
    renderReset("/reset-password?token=old");
    fillReset("new-password-1", "new-password-1");
    expect(await screen.findByText("reset.invalid_link")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "reset.request_new_link" })).toHaveAttribute("href", "/forgot-password");
  });
});
