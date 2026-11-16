import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { GamificationApi } from "@lingo/shared/api/gamification";
import type { GamificationState } from "@lingo/shared/api/types";
import { useOptionalAuth } from "../auth/AuthContext";

export const GAMIFICATION_KEY = ["gamification"] as const;

/** Server-reported flags + hearts/gems. Everything is hidden until it loads or
 *  when the server has the feature off (the query simply errors/returns false). */
export function useGamification(): GamificationState | undefined {
  const user = useOptionalAuth()?.user;
  const query = useQuery({
    queryKey: GAMIFICATION_KEY,
    queryFn: GamificationApi.state,
    enabled: !!user,
    retry: false,
    staleTime: 30_000,
  });
  return query.data;
}

/** "2h 15m" / "12m" / "<1m" for a heart refill countdown. Locale-neutral units. */
export function formatCountdown(targetIso: string | null, nowMs: number = Date.now()): string | null {
  if (!targetIso) return null;
  const ms = new Date(targetIso).getTime() - nowMs;
  if (!Number.isFinite(ms)) return null;
  const minutes = Math.ceil(Math.max(0, ms) / 60_000);
  if (minutes < 1) return "<1m";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

/** Returns a function that asks the server to restore a heart after practice or
 *  review work. A no-op when hearts are off or already full; the server decides. */
export function useHeartRestore(): () => void {
  const queryClient = useQueryClient();
  const state = useGamification();
  const active = !!state?.hearts.enabled && state.hearts.hearts < state.hearts.max_hearts;
  return useCallback(() => {
    if (!active) return;
    GamificationApi.restoreHeart()
      .then(() => queryClient.invalidateQueries({ queryKey: GAMIFICATION_KEY }))
      .catch(() => {
        /* best effort: practice must never fail because of a heart */
      });
  }, [active, queryClient]);
}
