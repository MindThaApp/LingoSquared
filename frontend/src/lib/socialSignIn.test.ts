import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { createNonce } from "./socialSignIn";

describe("createNonce", () => {
  it("hands the provider the SHA-256 hex digest of a fresh random nonce", async () => {
    const first = await createNonce();
    const second = await createNonce();
    expect(first.raw).toMatch(/^[A-Za-z0-9_-]{43}$/);
    expect(first.hashed).toBe(createHash("sha256").update(first.raw).digest("hex"));
    expect(second.raw).not.toBe(first.raw);
  });
});
