import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

let access = "expired";
let refresh: string | null = "r1";

class FakeAudio {
  static played: string[] = [];
  currentTime = 0;
  playbackRate = 1;
  src: string;
  constructor(src: string) {
    this.src = src;
  }
  addEventListener() {}
  pause() {}
  play() {
    FakeAudio.played.push(this.src);
    return Promise.resolve();
  }
}

function audioResponse() {
  return new Response(new Uint8Array([1, 2, 3]), {
    status: 200,
    headers: { "content-type": "audio/mpeg" },
  });
}

describe("speak() cloud TTS", () => {
  const speakSynth = { speak: vi.fn(), cancel: vi.fn(), getVoices: () => [{ lang: "nl-NL", voiceURI: "v" }] };

  beforeEach(async () => {
    vi.resetModules();
    const { configureApi } = await import("@lingo/shared/api/client");
    FakeAudio.played = [];
    speakSynth.speak.mockClear();
    access = "expired";
    refresh = "r1";
    configureApi({
      baseUrl: "http://api.test",
      tokenStorage: {
        get: () => access,
        set: (t: string) => {
          access = t;
        },
        clear: () => {
          access = "";
          refresh = null;
        },
        getRefresh: () => refresh,
        setRefresh: (t: string) => {
          refresh = t;
        },
      },
    } as never);
    vi.stubGlobal("Audio", FakeAudio);
    vi.stubGlobal("SpeechSynthesisUtterance", class { lang = ""; rate = 1; voice = null; text: string; constructor(t: string) { this.text = t; } });
    vi.stubGlobal("speechSynthesis", speakSynth);
    Object.defineProperty(window, "speechSynthesis", { value: speakSynth, configurable: true });
    URL.createObjectURL = vi.fn(() => "blob:test");
    URL.revokeObjectURL = vi.fn();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("refreshes on 401, retries /tts, and plays cloud audio (not browser voice)", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        calls.push(url);
        if (url.endsWith("/auth/refresh")) {
          return new Response(JSON.stringify({ access_token: "fresh", refresh_token: "r2" }), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }
        const auth = new Headers(init?.headers).get("Authorization");
        if (auth === "Bearer fresh") return audioResponse();
        return new Response("{}", { status: 401 });
      }),
    );
    const { speak } = await import("./tts");
    const ok = await speak("Lotte: hallo wereld", "nl");
    expect(ok).toBe(true);
    expect(calls.filter((u) => u.endsWith("/tts"))).toHaveLength(2);
    expect(FakeAudio.played).toEqual(["blob:test"]);
    expect(speakSynth.speak).not.toHaveBeenCalled();
    // sanitized text went to the server
    const body = JSON.parse(((fetch as unknown) as { mock: { calls: [string, RequestInit][] } }).mock.calls.find((c) => c[0].endsWith("/tts"))![1].body as string);
    expect(body.text).toBe("hallo wereld");
  });

  it("falls back without throwing on a malformed JSON body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("not json{", { status: 200, headers: { "content-type": "application/json" } })),
    );
    const { speak } = await import("./tts");
    await expect(speak("hallo", "nl")).resolves.toBe(true); // browser voice fallback
    expect(speakSynth.speak).toHaveBeenCalledTimes(1);
    expect(FakeAudio.played).toEqual([]);
  });
});
