import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import "../i18n";

const sentry = vi.hoisted(() => {
  let listener: ((p: unknown) => void) | null = null;
  return {
    sendProblemReport: vi.fn().mockResolvedValue(undefined),
    answerPendingCrash: vi.fn(),
    subscribePendingCrash: vi.fn((fn: (p: unknown) => void) => {
      listener = fn;
      fn(null);
      return () => {};
    }),
    emit: (p: unknown) => listener?.(p),
  };
});
vi.mock("../lib/sentry", () => sentry);

import { CrashReportPrompt } from "./CrashReportPrompt";
import { CrashReportSettings } from "./CrashReportSettings";
import { ReportProblem } from "./ReportProblem";

beforeEach(() => {
  localStorage.clear();
  sentry.sendProblemReport.mockClear();
  sentry.answerPendingCrash.mockClear();
});

describe("CrashReportPrompt", () => {
  it("is hidden until an error is pending, then asks", () => {
    render(<CrashReportPrompt />);
    expect(screen.queryByText("Send a crash report?")).toBeNull();
    act(() => sentry.emit({ error: new Error("x") }));
    expect(screen.getByText("Send a crash report?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(sentry.answerPendingCrash).toHaveBeenCalledWith(true);
  });

  it("'Never ask' stores never and declines", () => {
    render(<CrashReportPrompt />);
    act(() => sentry.emit({ error: new Error("x") }));
    fireEvent.click(screen.getByRole("button", { name: "Never ask" }));
    expect(localStorage.getItem("crash-report-consent")).toBe("never");
    expect(sentry.answerPendingCrash).toHaveBeenCalledWith(false);
  });
});

describe("CrashReportSettings", () => {
  it("defaults to Ask and persists a change", () => {
    render(<CrashReportSettings />);
    expect(screen.getByRole("radio", { name: "Ask me each time" })).toBeChecked();
    fireEvent.click(screen.getByRole("radio", { name: "Always send" }));
    expect(localStorage.getItem("crash-report-consent")).toBe("always");
    fireEvent.click(screen.getByRole("radio", { name: "Never send" }));
    expect(localStorage.getItem("crash-report-consent")).toBe("never");
    fireEvent.click(screen.getByRole("radio", { name: "Ask me each time" }));
    expect(localStorage.getItem("crash-report-consent")).toBeNull();
  });
});

describe("ReportProblem", () => {
  it("sends the message and optional email, regardless of consent", async () => {
    localStorage.setItem("crash-report-consent", "never");
    render(<ReportProblem />);
    fireEvent.click(screen.getByRole("button", { name: "Report a problem" }));
    const send = screen.getByRole("button", { name: "Send report" });
    expect(send).toBeDisabled();
    fireEvent.change(screen.getByLabelText("What went wrong?"), { target: { value: "  audio is silent " } });
    fireEvent.change(screen.getByLabelText("Your email (optional)"), { target: { value: "me@example.com" } });
    fireEvent.click(send);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Thanks, your report was sent."));
    expect(sentry.sendProblemReport).toHaveBeenCalledWith({ message: "audio is silent", email: "me@example.com" });
  });

  it("works without an email and shows an error when sending fails", async () => {
    sentry.sendProblemReport.mockRejectedValueOnce(new Error("offline"));
    render(<ReportProblem />);
    fireEvent.click(screen.getByRole("button", { name: "Report a problem" }));
    fireEvent.change(screen.getByLabelText("What went wrong?"), { target: { value: "broken" } });
    fireEvent.click(screen.getByRole("button", { name: "Send report" }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(sentry.sendProblemReport).toHaveBeenCalledWith({ message: "broken", email: "" });
  });
});
