import { createHash } from "node:crypto";
import { describe, expect, it, vi } from "vitest";
import { createNonce } from "./socialSignIn";

describe("createNonce", () => {
  it("uses the nonce the server issued and hands the provider its SHA-256 hex digest", async () => {
    const issue = vi
      .fn()
      .mockResolvedValueOnce({ nonce: "server-issued-nonce-one", expires_in: 600 })
      .mockResolvedValueOnce({ nonce: "server-issued-nonce-two", expires_in: 600 });
    const first = await createNonce(issue);
    const second = await createNonce(issue);
    expect(issue).toHaveBeenCalledTimes(2);
    expect(first.raw).toBe("server-issued-nonce-one");
    expect(first.hashed).toBe(createHash("sha256").update(first.raw).digest("hex"));
    expect(first.expiresInSeconds).toBe(600);
    expect(second.raw).not.toBe(first.raw);
  });

  it("fails when the server does not issue one", async () => {
    const issue = vi.fn().mockRejectedValue(new Error("503"));
    await expect(createNonce(issue)).rejects.toThrow("503");
  });
});
