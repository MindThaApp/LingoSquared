import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DeleteAccountConfirm } from "./DeleteAccountConfirm";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: { email?: string }) =>
      options?.email ? `${key}:${options.email}` : key,
  }),
}));

function renderDialog(overrides: Partial<React.ComponentProps<typeof DeleteAccountConfirm>> = {}) {
  const props = {
    email: "Learner@Example.com",
    isGuest: false,
    deleting: false,
    error: null,
    onCancel: vi.fn(),
    onConfirm: vi.fn(),
    ...overrides,
  };
  render(<DeleteAccountConfirm {...props} />);
  return props;
}

describe("DeleteAccountConfirm", () => {
  it("requires the account email, ignoring surrounding space and case", () => {
    const props = renderDialog();
    const confirm = screen.getByRole("button", { name: "profile.delete_confirm_button" });
    expect(confirm).toBeDisabled();

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "  learner@example.COM " } });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);
    expect(props.onConfirm).toHaveBeenCalledTimes(1);
  });

  it("lets guests confirm without exposing the email field", () => {
    const props = renderDialog({ isGuest: true });
    expect(screen.queryByRole("textbox")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "profile.delete_confirm_button" }));
    expect(props.onConfirm).toHaveBeenCalledTimes(1);
  });

  it("disables both actions while deleting and associates an error with the input", () => {
    renderDialog({ deleting: true, error: "Deletion failed" });
    expect(screen.getByRole("button", { name: "common.cancel" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "profile.delete_deleting" })).toBeDisabled();
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-describedby", "delete-confirm-error");
    expect(screen.getByRole("alert")).toHaveTextContent("Deletion failed");
  });
});
