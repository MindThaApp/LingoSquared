import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@lingo/shared/api/client";

const changePassword = vi.fn();
// Rejections come from a plain function, not from vi.fn()'s own result
// tracking, which would report a handled rejection as an unhandled one.
let rejectWith: unknown = null;
vi.mock("@lingo/shared/api/endpoints", () => ({
  AuthApi: {
    changePassword: async (...a: unknown[]) => {
      changePassword(...a);
      if (rejectWith) throw rejectWith;
      return {};
    },
  },
}));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

import { ChangePassword } from "./ChangePassword";

function fill(current: string, next: string, repeat: string) {
  fireEvent.change(screen.getByLabelText("account.current_password"), { target: { value: current } });
  fireEvent.change(screen.getByLabelText("account.new_password"), { target: { value: next } });
  fireEvent.change(screen.getByLabelText("account.confirm_password"), { target: { value: repeat } });
  fireEvent.submit(screen.getByRole("button", { name: "account.submit" }).closest("form")!);
}

describe("ChangePassword", () => {
  beforeEach(() => {
    changePassword.mockReset();
    rejectWith = null;
  });

  it("submits current and new password, then clears the form and confirms", async () => {
    render(<ChangePassword />);
    fill("old-password", "new-password-1", "new-password-1");
    await waitFor(() => expect(changePassword).toHaveBeenCalledWith("old-password", "new-password-1"));
    expect(await screen.findByText("account.success")).toBeInTheDocument();
    expect(screen.getByLabelText("account.current_password")).toHaveValue("");
  });

  it("rejects a mismatch or short password without calling the API", () => {
    render(<ChangePassword />);
    fill("old-password", "new-password-1", "different-one");
    expect(screen.getByRole("alert")).toHaveTextContent("account.mismatch");
    fill("old-password", "short", "short");
    expect(screen.getByRole("alert")).toHaveTextContent("account.too_short");
    expect(changePassword).not.toHaveBeenCalled();
  });

  it("rejects reusing the current password client-side", () => {
    render(<ChangePassword />);
    fill("same-password-1", "same-password-1", "same-password-1");
    expect(screen.getByRole("alert")).toHaveTextContent("account.same_as_current");
    expect(changePassword).not.toHaveBeenCalled();
  });

  it("shows a localized message for a wrong current password", async () => {
    rejectWith = new ApiError(403, "invalid_current_password", "x");
    render(<ChangePassword />);
    fill("bad-password", "new-password-1", "new-password-1");
    expect(await screen.findByRole("alert")).toHaveTextContent("account.wrong_current");
  });

  it("shows a rate-limit message on 429", async () => {
    rejectWith = new ApiError(429, "login_rate_limited", "x");
    render(<ChangePassword />);
    fill("bad-password", "new-password-1", "new-password-1");
    expect(await screen.findByRole("alert")).toHaveTextContent("account.rate_limited");
  });
});
