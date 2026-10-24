import { describe, expect, it } from "vitest";
import { REDACTED, scrubEvent, scrubString } from "./sentryScrub";

const JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.abcDEF123";

describe("scrubString", () => {
  it("masks emails, bearer tokens, JWTs and key=value secrets", () => {
    const out = scrubString(`mail a.b@example.com Bearer abcdef123456 jwt ${JWT} password=hunter2 token: xyz987`);
    expect(out).not.toMatch(/a\.b@example\.com|abcdef123456|hunter2|xyz987|eyJhbGci/);
    expect(out).toContain("[email]");
  });
});

describe("scrubEvent", () => {
  it("drops bodies, cookies, query strings and sensitive headers/fields", () => {
    const event = scrubEvent({
      request: {
        url: "https://app.test/lessons/1?token=abc#x",
        data: { answer: "de kat" },
        cookies: { sid: "1" },
        query_string: "token=abc",
        headers: { Authorization: `Bearer ${JWT}`, Cookie: "sid=1", "User-Agent": "UA" },
      },
      user: { id: "u1", email: "me@example.com", ip_address: "1.2.3.4" },
      extra: { user_answer: "mijn antwoord", refresh_token: "r", note: "ok" },
      exception: { values: [{ type: "TypeError", value: "bad for me@example.com" }] },
    });
    const blob = JSON.stringify(event);
    for (const leak of ["de kat", "me@example.com", "1.2.3.4", "mijn antwoord", "sid=1", "token=abc", JWT]) {
      expect(blob).not.toContain(leak);
    }
    expect(event.request.headers.Authorization).toBe(REDACTED);
    expect(event.request.headers.Cookie).toBe(REDACTED);
    expect(event.request.headers["User-Agent"]).toBe("UA");
    expect(event.user).toEqual({ id: "u1" });
    expect(event.extra.note).toBe("ok");
  });

  it("gives the same fingerprint to the same bug with different ids", () => {
    const make = (n: number, id: string) =>
      scrubEvent({ exception: { values: [{ type: "Error", value: `item ${n} ${id} missing` }] } });
    const a = make(12, "123e4567-e89b-12d3-a456-426614174000");
    const b = make(9, "123e4567-e89b-12d3-a456-426614174999");
    expect(a.fingerprint).toEqual(b.fingerprint);
  });

  it("keeps an existing fingerprint", () => {
    expect(scrubEvent({ fingerprint: ["x"], exception: { values: [{ type: "E", value: "v" }] } }).fingerprint).toEqual(["x"]);
  });
});
