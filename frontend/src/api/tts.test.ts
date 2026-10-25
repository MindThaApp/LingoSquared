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
    vi.stubEnv("VITE_PRERENDERED_AUDIO", "0"); // cloud-TTS tier tests; the pre-rendered tier has its own describe below
    vi.stubGlobal("Audio", FakeAudio);
    vi.stubGlobal("SpeechSynthesisUtterance", class { lang = ""; rate = 1; voice = null; text: string; constructor(t: string) { this.text = t; } });
    vi.stubGlobal("speechSynthesis", speakSynth);
    Object.defineProperty(window, "speechSynthesis", { value: speakSynth, configurable: true });
    URL.createObjectURL = vi.fn(() => "blob:test");
    URL.revokeObjectURL = vi.fn();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

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

  it("does not re-request a media asset that already 404'd", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url.includes("/media/")) return new Response("nope", { status: 404 });
      return audioResponse();
    });
    vi.stubGlobal("fetch", fetchMock);
    const { speak } = await import("./tts");
    await speak("hallo", "nl", "missing/key.mp3");
    await speak("hallo", "nl", "missing/key.mp3");
    const mediaCalls = fetchMock.mock.calls.filter((c) => String(c[0]).includes("/media/"));
    expect(mediaCalls).toHaveLength(1);
  });
});

describe("speak() fallback order with pre-rendered audio", () => {
  const synth = { speak: vi.fn(), cancel: vi.fn(), getVoices: () => [{ lang: "nl-NL", voiceURI: "v" }] };
  let missing: Set<string>;
  let played: string[];

  class OrderAudio {
    src: string;
    playbackRate = 1;
    preservesPitch = false;
    currentTime = 0;
    constructor(src: string) {
      this.src = src;
    }
    addEventListener() {}
    pause() {}
    play() {
      played.push(this.src);
      if (this.src.includes("/media/audio/") && missing.has(this.src)) {
        return Promise.reject(new DOMException("404", "NotSupportedError"));
      }
      return Promise.resolve();
    }
  }

  beforeEach(async () => {
    vi.resetModules();
    const { configureApi } = await import("@lingo/shared/api/client");
    configureApi({
      baseUrl: "http://api.test",
      tokenStorage: { get: () => "t", set: () => {}, clear: () => {}, getRefresh: () => null, setRefresh: () => {} },
    } as never);
    missing = new Set();
    played = [];
    synth.speak.mockClear();
    vi.stubGlobal("Audio", OrderAudio);
    vi.stubGlobal("SpeechSynthesisUtterance", class { lang = ""; rate = 1; voice = null; text: string; constructor(t: string) { this.text = t; } });
    Object.defineProperty(window, "speechSynthesis", { value: synth, configurable: true });
    URL.createObjectURL = vi.fn(() => "blob:tts");
    URL.revokeObjectURL = vi.fn();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("plays the pre-rendered clip first and never calls /tts", async () => {
    const fetchMock = vi.fn(async () => new Response("{}", { status: 500 }));
    vi.stubGlobal("fetch", fetchMock);
    const { speak } = await import("./tts");
    const { prerenderedAudioUrl } = await import("../lib/prerenderedAudio");
    expect(await speak("Lotte: hallo wereld", "nl")).toBe(true);
    const expected = prerenderedAudioUrl("hallo wereld", "nl", "http://localhost:8000");
    expect(expected).toMatch(/\/media\/audio\/[0-9a-f]{32}\.mp3$/);
    expect(played).toEqual([expected]);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("falls back to /tts when the clip is missing, then remembers the miss", async () => {
    const fetchMock = vi.fn(
      async () => new Response(new Uint8Array([1]), { status: 200, headers: { "content-type": "audio/mpeg" } }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { prerenderedAudioUrl } = await import("../lib/prerenderedAudio");
    missing.add(prerenderedAudioUrl("goedemorgen", "nl", "http://localhost:8000")!);
    const { speak } = await import("./tts");
    expect(await speak("goedemorgen", "nl")).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1); // POST /tts
    expect(played).toHaveLength(2); // failed clip, then blob from /tts
    expect(played[1]).toBe("blob:tts");
    played.length = 0;
    await speak("goedemorgen", "nl");
    expect(played.some((u) => u.includes("/media/audio/"))).toBe(false); // negative cache
  });

  it("falls back to browser speech when the clip and /tts both fail", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 500 })));
    const { prerenderedAudioUrl } = await import("../lib/prerenderedAudio");
    missing.add(prerenderedAudioUrl("hallo", "nl", "http://localhost:8000")!);
    const { speak } = await import("./tts");
    expect(await speak("hallo", "nl")).toBe(true);
    expect(synth.speak).toHaveBeenCalledTimes(1);
  });

  it("applies the speed preference through playbackRate", async () => {
    vi.stubGlobal("fetch", vi.fn());
    const instances: OrderAudio[] = [];
    vi.stubGlobal("Audio", class extends OrderAudio { constructor(s: string) { super(s); instances.push(this); } });
    const { speak } = await import("./tts");
    await speak("hallo", "nl");
    expect(instances[0].preservesPitch).toBe(true);
    expect(instances[0].playbackRate).toBeGreaterThan(0);
  });

  it("is switched off by VITE_PRERENDERED_AUDIO=0", async () => {
    vi.stubEnv("VITE_PRERENDERED_AUDIO", "0");
    const { prerenderedAudioUrl } = await import("../lib/prerenderedAudio");
    expect(prerenderedAudioUrl("hallo", "nl", "http://x")).toBeNull();
  });

  it("honours VITE_AUDIO_BASE_URL and has no clip for languages without a voice", async () => {
    vi.stubEnv("VITE_AUDIO_BASE_URL", "/media/audio/");
    const { prerenderedAudioUrl } = await import("../lib/prerenderedAudio");
    expect(prerenderedAudioUrl("hallo", "nl", "http://x")).toMatch(/^\/media\/audio\/[0-9a-f]{32}\.mp3$/);
    expect(prerenderedAudioUrl("你好", "zh", "http://x")).toBeNull();
  });
});
