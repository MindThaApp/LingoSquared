// Answer-submit error codes after which a practice item can never be answered
// again (retrying is pointless): gone, already answered, or expired.
//
// NOTE: frontend/src/pages/PracticeFeedPage.tsx still has its own private copy
// of this set. It should import this one in a follow-up (pages/ was out of
// scope when this was extracted).
export const PERMANENT_ANSWER_ERROR_CODES = new Set([
  "practice_item_not_found",
  "practice_item_answered",
  "practice_item_expired",
]);
