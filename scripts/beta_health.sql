-- ============================================================================
-- beta_health.sql — minimal beta-health check for Lingo²
--
-- Answers basic product-health questions from existing tables only (no
-- analytics/event-tracking infrastructure exists; this queries the real
-- operational tables defined in backend/app/models/entities.py).
--
-- How to run (local dev stack; db service has no bind mount, so pipe the
-- file in via stdin rather than psql -f):
--
--   cd backend && docker compose exec -T db \
--     psql -U lingosquared -d lingosquared -v ON_ERROR_STOP=1 \
--     < ../scripts/beta_health.sql
--
-- (User/db names are the docker-compose.yml defaults POSTGRES_USER /
-- POSTGRES_DB = lingosquared unless overridden in backend/.env.)
--
-- Read-only: every statement is a SELECT. Safe to run against any stack.
--
-- Timezone caveat: all timestamps are timestamptz and now()/CURRENT_DATE
-- evaluate in the server's timezone (UTC in the containers). "Days" here
-- are UTC days, not each user's own timezone (User.timezone is only used
-- by the app's streak logic, not by this report).
-- ============================================================================

\echo ''
\echo '=== 1. Daily signups (last 30 days, by UTC day) ==='
SELECT
    date_trunc('day', created_at)::date AS signup_day,
    COUNT(*)                            AS signups
FROM users
WHERE created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY 1 DESC;

\echo ''
\echo '=== 1b. Signup totals (7 / 30 days, all time) ==='
SELECT
    COUNT(*) FILTER (WHERE created_at >= now() - interval '7 days')  AS signups_7d,
    COUNT(*) FILTER (WHERE created_at >= now() - interval '30 days') AS signups_30d,
    COUNT(*)                                                         AS signups_all_time
FROM users;

\echo ''
\echo '=== 2. Activation: % of users completing their first lesson within 24h of registration ==='
-- Only users registered more than 24h ago are eligible (newer accounts have
-- not had their full window yet and would unfairly drag the rate down).
WITH first_completion AS (
    SELECT user_id, MIN(completed_at) AS first_completed_at
    FROM lesson_progress
    WHERE completed_at IS NOT NULL
    GROUP BY user_id
)
SELECT
    COUNT(*)                                            AS eligible_users,
    COUNT(fc.user_id)                                   AS ever_completed_a_lesson,
    COUNT(*) FILTER (
        WHERE fc.first_completed_at <= u.created_at + interval '24 hours'
    )                                                   AS completed_within_24h,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE fc.first_completed_at <= u.created_at + interval '24 hours'
        ) / NULLIF(COUNT(*), 0),
        1
    )                                                   AS pct_completed_within_24h
FROM users u
LEFT JOIN first_completion fc ON fc.user_id = u.id
WHERE u.created_at <= now() - interval '24 hours';

\echo ''
\echo '=== 3. DAU / WAU (distinct users with any learning activity) ==='
-- Activity = any exercise attempt, practice/checkpoint answer, lesson
-- start/completion, checkpoint start, SRS review, or quest award.
WITH activity AS (
    SELECT user_id, created_at AS at FROM exercise_attempts
    UNION ALL
    SELECT user_id, created_at FROM practice_attempts
    UNION ALL
    SELECT user_id, started_at FROM lesson_progress WHERE started_at IS NOT NULL
    UNION ALL
    SELECT user_id, completed_at FROM lesson_progress WHERE completed_at IS NOT NULL
    UNION ALL
    SELECT user_id, created_at FROM checkpoint_attempts
    UNION ALL
    SELECT user_id, last_reviewed_at FROM user_lexeme_srs WHERE last_reviewed_at IS NOT NULL
    UNION ALL
    SELECT user_id, awarded_at FROM quest_completions
)
SELECT
    COUNT(DISTINCT user_id) FILTER (WHERE at >= now() - interval '1 day')  AS dau_last_24h,
    COUNT(DISTINCT user_id) FILTER (WHERE at >= now() - interval '7 days') AS wau_last_7d
FROM activity;

\echo ''
\echo '=== 4. Per-exercise-type failure rate (compiled lesson exercises) ==='
SELECT
    e.type                                                        AS exercise_type,
    COUNT(*)                                                      AS attempts,
    COUNT(*) FILTER (WHERE ea.correct)                            AS correct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE NOT ea.correct)
          / NULLIF(COUNT(*), 0), 1)                               AS failure_pct
FROM exercise_attempts ea
JOIN exercises e ON e.id = ea.exercise_id
GROUP BY e.type
ORDER BY failure_pct DESC NULLS LAST, attempts DESC;

\echo ''
\echo '=== 4b. Per-type failure rate (generated practice/review/checkpoint items) ==='
-- Same question for the Endless Practice engine's generated items (these
-- never touch exercise_attempts; type lives on the practice template).
SELECT
    pt.type                                                       AS item_type,
    pi.source                                                     AS source,
    COUNT(*)                                                      AS attempts,
    COUNT(*) FILTER (WHERE pa.correct)                            AS correct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE NOT pa.correct)
          / NULLIF(COUNT(*), 0), 1)                               AS failure_pct
FROM practice_attempts pa
JOIN practice_items pi     ON pi.id = pa.practice_item_id
JOIN practice_templates pt ON pt.id = pi.template_id
GROUP BY pt.type, pi.source
ORDER BY failure_pct DESC NULLS LAST, attempts DESC;

\echo ''
\echo '=== 5. Crash canary: exercises with ZERO attempts in lessons real users completed ==='
-- Completing a lesson requires answering every exercise in it, so an
-- exercise with zero attempts (across ALL users, all time) inside a lesson
-- that >=1 user has completed means that exercise is being silently
-- skipped/crashed by the frontend — the historical failure mode of an
-- unregistered exercise type. Empty result = healthy.
-- Known false positive on dev DBs: test accounts whose lesson completion
-- was driven via curl against POST /lessons/{id}/complete (no exercises
-- answered) show whole lessons here. A REAL renderer bug looks like one
-- specific type at zero while sibling exercises in the same lesson have
-- attempts — check the 5b rollup for a type-shaped pattern.
WITH lesson_traffic AS (
    SELECT
        lp.lesson_id,
        COUNT(DISTINCT lp.user_id) FILTER (WHERE lp.completed_at IS NOT NULL) AS completing_users,
        COUNT(DISTINCT lp.user_id)                                            AS visiting_users
    FROM lesson_progress lp
    GROUP BY lp.lesson_id
),
attempt_counts AS (
    SELECT exercise_id, COUNT(*) AS attempts
    FROM exercise_attempts
    GROUP BY exercise_id
)
SELECT
    e.type                          AS exercise_type,
    c.title                         AS course,
    u.title                         AS unit,
    l.title                         AS lesson,
    e."order"                       AS exercise_order,
    e.id                            AS exercise_id,
    lt.completing_users,
    lt.visiting_users
FROM exercises e
JOIN lessons l        ON l.id = e.lesson_id
JOIN units u          ON u.id = l.unit_id
JOIN courses c        ON c.id = u.course_id
JOIN lesson_traffic lt ON lt.lesson_id = l.id
LEFT JOIN attempt_counts ac ON ac.exercise_id = e.id
WHERE COALESCE(ac.attempts, 0) = 0
  AND lt.completing_users >= 1
ORDER BY lt.completing_users DESC, c.title, u.title, l.title, e."order"
LIMIT 50;

\echo ''
\echo '=== 5b. Crash canary rollup by exercise type ==='
-- If one TYPE dominates here, that renderer is probably broken.
WITH lesson_traffic AS (
    SELECT
        lp.lesson_id,
        COUNT(DISTINCT lp.user_id) FILTER (WHERE lp.completed_at IS NOT NULL) AS completing_users
    FROM lesson_progress lp
    GROUP BY lp.lesson_id
),
attempt_counts AS (
    SELECT exercise_id, COUNT(*) AS attempts
    FROM exercise_attempts
    GROUP BY exercise_id
)
SELECT
    e.type   AS exercise_type,
    COUNT(*) AS zero_attempt_exercises_in_completed_lessons
FROM exercises e
JOIN lesson_traffic lt ON lt.lesson_id = e.lesson_id
LEFT JOIN attempt_counts ac ON ac.exercise_id = e.id
WHERE COALESCE(ac.attempts, 0) = 0
  AND lt.completing_users >= 1
GROUP BY e.type
ORDER BY 2 DESC;

\echo ''
\echo '=== 6. Checkpoint pass rate ==='
-- passed IS NULL = started but never scored (abandoned mid-checkpoint).
SELECT
    COUNT(*)                                            AS attempts_total,
    COUNT(*) FILTER (WHERE passed IS NULL)              AS unscored_abandoned,
    COUNT(*) FILTER (WHERE passed IS NOT NULL)          AS scored,
    COUNT(*) FILTER (WHERE passed)                      AS passed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE passed)
          / NULLIF(COUNT(*) FILTER (WHERE passed IS NOT NULL), 0), 1)
                                                        AS pass_pct_of_scored,
    ROUND(AVG(score) FILTER (WHERE score IS NOT NULL)::numeric, 3)
                                                        AS avg_score
FROM checkpoint_attempts;

\echo ''
\echo '=== 6b. Checkpoint pass rate by unit ==='
SELECT
    c.title                                             AS course,
    u.title                                             AS unit,
    COUNT(*) FILTER (WHERE ca.passed IS NOT NULL)       AS scored,
    COUNT(*) FILTER (WHERE ca.passed)                   AS passed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE ca.passed)
          / NULLIF(COUNT(*) FILTER (WHERE ca.passed IS NOT NULL), 0), 1)
                                                        AS pass_pct,
    ROUND(AVG(ca.score) FILTER (WHERE ca.score IS NOT NULL)::numeric, 3)
                                                        AS avg_score
FROM checkpoint_attempts ca
JOIN units u   ON u.id = ca.unit_id
JOIN courses c ON c.id = u.course_id
GROUP BY c.title, u.title
ORDER BY scored DESC, c.title, u.title;

\echo ''
\echo '=== 7. Open content-issue reports, grouped by exercise ==='
SELECT
    e.type                        AS exercise_type,
    c.title                       AS course,
    l.title                       AS lesson,
    cir.exercise_id,
    COUNT(*)                      AS open_reports,
    MIN(cir.created_at)           AS oldest_report
FROM content_issue_reports cir
JOIN exercises e ON e.id = cir.exercise_id
JOIN lessons l   ON l.id = e.lesson_id
JOIN units u     ON u.id = l.unit_id
JOIN courses c   ON c.id = u.course_id
WHERE cir.status = 'open'
GROUP BY e.type, c.title, l.title, cir.exercise_id
ORDER BY open_reports DESC, oldest_report
LIMIT 50;

\echo ''
\echo '=== 7b. Open report totals by target kind and category ==='
SELECT
    CASE
        WHEN exercise_id      IS NOT NULL THEN 'exercise'
        WHEN practice_item_id IS NOT NULL THEN 'practice_item'
        ELSE 'page_feedback'
    END                           AS target_kind,
    category,
    COUNT(*)                      AS open_reports
FROM content_issue_reports
WHERE status = 'open'
GROUP BY 1, 2
ORDER BY open_reports DESC;

\echo ''
\echo '=== 8. SRS review-loop health (bonus retention signal) ==='
SELECT
    COUNT(*)                                                  AS tracked_lexeme_rows,
    COUNT(DISTINCT user_id)                                   AS users_with_srs,
    COUNT(*) FILTER (WHERE NOT suspended AND due_at <= now()) AS due_now,
    COUNT(*) FILTER (
        WHERE NOT suspended AND due_at <= now() - interval '7 days'
    )                                                         AS overdue_7d_plus
FROM user_lexeme_srs;
