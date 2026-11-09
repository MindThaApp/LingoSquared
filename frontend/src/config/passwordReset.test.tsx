import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { isPasswordResetEnabled } from "./passwordReset";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    loading: false,
    sessionUnavailable: false,
    login: vi.fn(),
    loginWithGoogle: vi.fn(),
    loginWithApple: vi.fn(),
    startGuest: vi.fn(),
    retrySession: vi.fn(),
  }),
}));

import { LoginPage } from "../pages/LoginPage";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("password reset flag", () => {
  it("is off by default", () => {
    vi.stubEnv("VITE_PASSWORD_RESET_ENABLED", "");
    expect(isPasswordResetEnabled()).toBe(false);
  });

  it("only the string 'true' enables it", () => {
    vi.stubEnv("VITE_PASSWORD_RESET_ENABLED", "1");
    expect(isPasswordResetEnabled()).toBe(false);
    vi.stubEnv("VITE_PASSWORD_RESET_ENABLED", "true");
    expect(isPasswordResetEnabled()).toBe(true);
  });

  it("hides the forgot-password link on the login page when off", () => {
    vi.stubEnv("VITE_PASSWORD_RESET_ENABLED", "");
    render(<MemoryRouter><LoginPage /></MemoryRouter>);
    expect(screen.queryByText("reset.forgot_link")).toBeNull();
  });

  it("shows the link when enabled", () => {
    vi.stubEnv("VITE_PASSWORD_RESET_ENABLED", "true");
    render(<MemoryRouter><LoginPage /></MemoryRouter>);
    expect(screen.getByText("reset.forgot_link")).toBeTruthy();
  });
});
