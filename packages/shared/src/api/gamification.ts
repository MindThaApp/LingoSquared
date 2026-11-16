import { get, post, put } from "./client";
import type {
  GamificationState,
  GemSpendItem,
  GemSpendResult,
  HeartRestoreResult,
  Leaderboard,
} from "./types";

// Hearts / gems / weekly leaderboard. Kept out of endpoints.ts so the optional,
// flag-gated feature stays self-contained. Every call is server-authoritative.
function operationId(): string {
  // Idempotency key for a spend: a retry of the SAME click reuses it.
  const c = (globalThis as { crypto?: { randomUUID?: () => string } }).crypto;
  return c?.randomUUID ? c.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

export const GamificationApi = {
  state: () => get<GamificationState>("/me/gamification"),
  // Asks the server to restore one heart for finished practice/review work; it
  // counts the learner's real practice answers itself.
  restoreHeart: () => post<HeartRestoreResult>("/me/hearts/practice-restore"),
  spend: (item: GemSpendItem, clientOperationId: string = operationId()) =>
    post<GemSpendResult>("/me/gems/spend", { item, client_operation_id: clientOperationId }),
  leaderboard: () => get<Leaderboard>("/leaderboard/weekly"),
  setLeaderboardOptOut: (opted_out: boolean) =>
    put<{ opted_out: boolean }>("/me/leaderboard-privacy", { opted_out }),
};
