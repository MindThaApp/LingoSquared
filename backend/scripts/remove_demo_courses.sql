-- =====================================================================
-- remove_demo_courses.sql — one-off cleanup of the 4 seeded DEMO courses
-- =====================================================================
--
-- WHY THIS EXISTS
-- ---------------
-- `backend/app/content/seed.py` used to create 4 tiny hardcoded demo
-- courses on every deploy, alongside the required Language/Achievement
-- bootstrap:
--
--     en -> fa   "Farsi Foundations"                        (A1)
--     en -> prs  "Dari Foundations"                         (A1)
--     en -> prs  "Dari Elementary"                          (A2)
--     prs -> en  "English Foundations for Dari Speakers"    (A1)
--
-- On the live server they appear in the course picker BESIDE the real
-- launch courses, and because `/courses` orders by (level, title) the
-- Latin-titled "English Foundations for Dari Speakers" sorts BEFORE the
-- real Arabic-titled "انگلیسی A1" — so CoursePickerPage's "start here"
-- hint (pinned to index 0) points a Dari speaker at a 2-lesson stub.
--
-- The seed script no longer creates them (2026-07-22, CLI default is now
-- OFF; `--with-demo-courses` / LINGO_SEED_DEMO_COURSES=1 opts back in for
-- dev/CI). But seeding is deliberately create-missing-only and there is
-- NO delete-course endpoint, so the rows already in the live and dev
-- databases need this one-off script.
--
--
-- HOW TO RUN IT
-- -------------
-- As written this file is a DRY RUN: it opens a transaction, prints
-- what it would delete, deletes it, prints the after-state, and then
-- ROLLBACKs. Nothing is persisted.
--
--     docker compose exec -T db psql -U lingosquared -d lingosquared \
--       -v ON_ERROR_STOP=1 < backend/scripts/remove_demo_courses.sql
--
-- To actually commit: TAKE A BACKUP FIRST (scripts/backup_db.sh), then
-- change the final `ROLLBACK;` on the last line to `COMMIT;` and re-run
-- the exact same command. That two-character edit is the only way to
-- make this destructive — deliberately, so it can never happen by
-- passing the wrong flag.
--
-- Running it against the LIVE database is a destructive live-DB
-- operation and requires Ramin present (root CLAUDE.md, "Deploy
-- authority"). See docs/PRE_DEPLOY_RUNBOOK.md → "Removing the
-- already-seeded demo courses".
--
--
-- HOW THE COURSES ARE IDENTIFIED (read this before approving)
-- -----------------------------------------------------------
-- NOT by a title LIKE pattern. The `courses` table has no `content_key`
-- column (only units/lessons/exercises do — see models/entities.py), so
-- the selector is:
--
--   (a) an EXACT match on the (source_language, target_language, title)
--       triple, which is the table's own natural key
--       (UniqueConstraint("source_language","target_language","title")),
--       for the 4 literal demo titles — no wildcards, no LIKE; AND
--   (b) the course has NO unit carrying a non-NULL `content_key`.
--       Every course produced by the real pipeline
--       (scripts/compile_content.py -> POST /admin/content/import)
--       carries per-unit keys like 'fa.a1.unit01'; the hardcoded demo
--       dicts in seed.py never set one. This is the `content_key IS
--       NULL` half of the selector, applied at the level where
--       content_key actually exists.
--
-- Three guards then ABORT the whole transaction rather than delete
-- anything questionable:
--   1. more than 4 courses matched;
--   2. a matched course has more than 5 units (real courses have ~50 —
--      this would mean (b) failed to discriminate);
--   3. a matched course has any Lexeme or PracticeTemplate rows (real
--      launch courses always do after the backfill step; demo courses
--      never do).
--
-- Known live IDs from the 2026-07-22 audit, for cross-checking the
-- dry-run output — NOT used as the selector, because the dev DB's IDs
-- differ and only the first 8 hex characters of each were recorded:
--   683a90fe…  Farsi Foundations
--   c9bacfb5…  Dari Foundations
--   a2af2c0a…  Dari Elementary
--   138e9b66…  English Foundations for Dari Speakers
-- If the dry run does not match this set, STOP and re-audit.
--
-- Idempotent: re-running after a successful commit matches 0 courses
-- and deletes nothing.
-- =====================================================================

\set ON_ERROR_STOP on

BEGIN;

-- ---------------------------------------------------------------------
-- 1. Resolve the target set.
-- ---------------------------------------------------------------------
CREATE TEMP TABLE demo_courses ON COMMIT DROP AS
SELECT c.id, c.source_language, c.target_language, c.title, c.level
FROM courses c
WHERE (c.source_language, c.target_language, c.title) IN (
        ('en',  'fa',  'Farsi Foundations'),
        ('en',  'prs', 'Dari Foundations'),
        ('en',  'prs', 'Dari Elementary'),
        ('prs', 'en',  'English Foundations for Dari Speakers')
      )
  AND NOT EXISTS (
        SELECT 1 FROM units u
        WHERE u.course_id = c.id
          AND u.content_key IS NOT NULL
      );

CREATE TEMP TABLE demo_units ON COMMIT DROP AS
SELECT u.id FROM units u JOIN demo_courses d ON d.id = u.course_id;

CREATE TEMP TABLE demo_lessons ON COMMIT DROP AS
SELECT l.id FROM lessons l JOIN demo_units u ON u.id = l.unit_id;

CREATE TEMP TABLE demo_exercises ON COMMIT DROP AS
SELECT e.id FROM exercises e JOIN demo_lessons l ON l.id = e.lesson_id;

CREATE TEMP TABLE demo_lexemes ON COMMIT DROP AS
SELECT x.id FROM lexemes x JOIN demo_courses d ON d.id = x.course_id
UNION
SELECT x.id FROM lexemes x JOIN demo_lessons l ON l.id = x.provenance_lesson_id;

CREATE TEMP TABLE demo_templates ON COMMIT DROP AS
SELECT t.id FROM practice_templates t JOIN demo_courses d ON d.id = t.course_id
UNION
SELECT t.id FROM practice_templates t JOIN demo_lessons l ON l.id = t.provenance_lesson_id;

CREATE TEMP TABLE demo_practice_items ON COMMIT DROP AS
SELECT p.id FROM practice_items p JOIN demo_courses d ON d.id = p.course_id
UNION
SELECT p.id FROM practice_items p JOIN demo_templates t ON t.id = p.template_id
UNION
SELECT p.id FROM practice_items p JOIN demo_lexemes x ON x.id = p.target_lexeme_id;

CREATE TEMP TABLE demo_content_items ON COMMIT DROP AS
SELECT ci.id FROM content_items ci JOIN demo_courses d ON d.id = ci.course_id
UNION
SELECT ci.id FROM content_items ci JOIN demo_lessons l ON l.id = ci.lesson_id;

-- ---------------------------------------------------------------------
-- 2. Show the human exactly what matched, BEFORE anything is deleted.
-- ---------------------------------------------------------------------
\echo ''
\echo '=== Courses matched (expect exactly these 4, or 0 if already cleaned) ==='
SELECT id, source_language AS src, target_language AS tgt, title, level
FROM demo_courses
ORDER BY source_language, target_language, level, title;

\echo ''
\echo '=== Dependent row counts that will be removed ==='
SELECT 'courses'         AS entity, (SELECT count(*) FROM demo_courses)        AS rows
UNION ALL SELECT 'units',           (SELECT count(*) FROM demo_units)
UNION ALL SELECT 'lessons',         (SELECT count(*) FROM demo_lessons)
UNION ALL SELECT 'exercises',       (SELECT count(*) FROM demo_exercises)
UNION ALL SELECT 'content_items',   (SELECT count(*) FROM demo_content_items)
UNION ALL SELECT 'lexemes',         (SELECT count(*) FROM demo_lexemes)
UNION ALL SELECT 'practice_templates', (SELECT count(*) FROM demo_templates)
UNION ALL SELECT 'practice_items',  (SELECT count(*) FROM demo_practice_items);

\echo ''
\echo '=== Learner data attached to these courses (should normally be 0) ==='
SELECT 'lesson_progress'  AS entity,
       (SELECT count(*) FROM lesson_progress WHERE lesson_id IN (SELECT id FROM demo_lessons)) AS rows
UNION ALL SELECT 'exercise_attempts',
       (SELECT count(*) FROM exercise_attempts WHERE exercise_id IN (SELECT id FROM demo_exercises))
UNION ALL SELECT 'skill_progress',
       (SELECT count(*) FROM skill_progress WHERE course_id IN (SELECT id FROM demo_courses))
UNION ALL SELECT 'user_lexeme_srs',
       (SELECT count(*) FROM user_lexeme_srs
        WHERE lexeme_id IN (SELECT id FROM demo_lexemes)
           OR course_id IN (SELECT id FROM demo_courses))
UNION ALL SELECT 'content_issue_reports',
       (SELECT count(*) FROM content_issue_reports
        WHERE exercise_id IN (SELECT id FROM demo_exercises)
           OR practice_item_id IN (SELECT id FROM demo_practice_items));

-- ---------------------------------------------------------------------
-- 3. Guards — abort the whole transaction rather than delete anything
--    that does not look exactly like the audited demo-course set.
-- ---------------------------------------------------------------------
DO $guard$
DECLARE
    matched     int;
    bad_id      text;
    bad_title   text;
    bad_count   bigint;
BEGIN
    SELECT count(*) INTO matched FROM demo_courses;

    IF matched > 4 THEN
        RAISE EXCEPTION
            'ABORT: % courses matched, expected at most 4. The selector is '
            'not discriminating — re-audit before running this script.', matched;
    END IF;

    -- Guard 2: a matched course with a realistic unit count is not a demo.
    SELECT d.id, d.title, count(u.id)
      INTO bad_id, bad_title, bad_count
      FROM demo_courses d
      JOIN units u ON u.course_id = d.id
     GROUP BY d.id, d.title
    HAVING count(u.id) > 5
     LIMIT 1;

    IF bad_id IS NOT NULL THEN
        RAISE EXCEPTION
            'ABORT: matched course % (%) has % units. Real courses have ~50 — '
            'this is almost certainly NOT a demo course.',
            bad_id, bad_title, bad_count;
    END IF;

    -- Guard 3: lexemes / practice templates only exist for real content.
    bad_id := NULL; bad_title := NULL;
    SELECT d.id, d.title
      INTO bad_id, bad_title
      FROM demo_courses d
     WHERE EXISTS (SELECT 1 FROM lexemes x WHERE x.course_id = d.id)
        OR EXISTS (SELECT 1 FROM practice_templates t WHERE t.course_id = d.id)
     LIMIT 1;

    IF bad_id IS NOT NULL THEN
        RAISE EXCEPTION
            'ABORT: matched course % (%) has Lexeme/PracticeTemplate rows, which '
            'only the real content pipeline creates. Re-audit before deleting.',
            bad_id, bad_title;
    END IF;

    RAISE NOTICE 'Guards passed: % demo course(s) will be removed.', matched;
END
$guard$;

-- ---------------------------------------------------------------------
-- 4. Delete, bottom-up. Order matters: several FKs are ON DELETE RESTRICT
--    (lexemes.provenance_lesson_id, practice_templates.provenance_lesson_id,
--    user_lexeme_srs.lexeme_id, practice_items.template_id/target_lexeme_id,
--    practice_attempts.practice_item_id, exercise_attempts.exercise_id,
--    content_issue_reports.exercise_id/practice_item_id), so relying on
--    cascade from `DELETE FROM courses` alone would fail.
--    Every statement is a no-op on an already-cleaned database.
-- ---------------------------------------------------------------------

-- 4a. Feedback: reports RESTRICT on exercises/practice_items.
--     feedback_attachments CASCADE from the report, deleted explicitly
--     anyway so the row count is visible in the psql output.
DELETE FROM feedback_attachments
 WHERE report_id IN (
       SELECT id FROM content_issue_reports
        WHERE exercise_id IN (SELECT id FROM demo_exercises)
           OR practice_item_id IN (SELECT id FROM demo_practice_items));

DELETE FROM content_issue_reports
 WHERE exercise_id IN (SELECT id FROM demo_exercises)
    OR practice_item_id IN (SELECT id FROM demo_practice_items);

-- 4b. Endless-practice chain: attempts -> items -> templates.
DELETE FROM practice_attempts
 WHERE practice_item_id IN (SELECT id FROM demo_practice_items);

DELETE FROM practice_items
 WHERE id IN (SELECT id FROM demo_practice_items);

DELETE FROM practice_templates
 WHERE id IN (SELECT id FROM demo_templates);

-- 4c. Lexeme SRS chain: user_lexeme_srs RESTRICTs on lexemes.
DELETE FROM user_lexeme_srs
 WHERE lexeme_id IN (SELECT id FROM demo_lexemes)
    OR course_id  IN (SELECT id FROM demo_courses);

DELETE FROM lexemes
 WHERE id IN (SELECT id FROM demo_lexemes);

-- 4d. Per-exercise learner data: exercise_attempts RESTRICTs on exercises.
--     content_issue_reports.attempt_id is ON DELETE SET NULL, and every
--     report pointing at these exercises is already gone (4a).
DELETE FROM exercise_attempts
 WHERE exercise_id IN (SELECT id FROM demo_exercises);

DELETE FROM review_items
 WHERE exercise_id IN (SELECT id FROM demo_exercises);

-- 4e. Per-lesson / per-unit learner data.
DELETE FROM lesson_progress
 WHERE lesson_id IN (SELECT id FROM demo_lessons);

DELETE FROM checkpoint_attempts
 WHERE unit_id IN (SELECT id FROM demo_units);

-- 4f. Teaching material and its progress rows.
DELETE FROM vocabulary_progress
 WHERE content_item_id IN (SELECT id FROM demo_content_items);

DELETE FROM grammar_progress
 WHERE content_item_id IN (SELECT id FROM demo_content_items);

DELETE FROM content_items
 WHERE id IN (SELECT id FROM demo_content_items);

-- 4g. The content tree itself.
DELETE FROM exercises WHERE id IN (SELECT id FROM demo_exercises);
DELETE FROM lessons   WHERE id IN (SELECT id FROM demo_lessons);
DELETE FROM units     WHERE id IN (SELECT id FROM demo_units);

-- 4h. Per-course learner data, then the courses.
DELETE FROM skill_progress
 WHERE course_id IN (SELECT id FROM demo_courses);

-- content_keys.entity_id is a plain column with no FK, so nothing else
-- cleans these up. Nothing in app/ currently writes ContentKey rows, so
-- this is normally a 0-row no-op — kept so a future writer can't leave
-- keys dangling at deleted ids.
DELETE FROM content_keys
 WHERE entity_type = 'unit'     AND entity_id IN (SELECT id FROM demo_units);
DELETE FROM content_keys
 WHERE entity_type = 'lesson'   AND entity_id IN (SELECT id FROM demo_lessons);
DELETE FROM content_keys
 WHERE entity_type = 'exercise' AND entity_id IN (SELECT id FROM demo_exercises);

DELETE FROM courses WHERE id IN (SELECT id FROM demo_courses);

-- ---------------------------------------------------------------------
-- 5. Verify. Expect 0 rows from the first query, and the real launch
--    courses still present in the second.
-- ---------------------------------------------------------------------
\echo ''
\echo '=== AFTER: demo courses still present (expect 0 rows) ==='
SELECT id, source_language AS src, target_language AS tgt, title
FROM courses
WHERE (source_language, target_language, title) IN (
        ('en',  'fa',  'Farsi Foundations'),
        ('en',  'prs', 'Dari Foundations'),
        ('en',  'prs', 'Dari Elementary'),
        ('prs', 'en',  'English Foundations for Dari Speakers')
      );

\echo ''
\echo '=== AFTER: surviving courses for the three affected directions ==='
\echo '=== (the real launch courses MUST all still be here) ==='
SELECT c.source_language AS src, c.target_language AS tgt, c.title, c.level,
       (SELECT count(*) FROM units u WHERE u.course_id = c.id) AS units
FROM courses c
WHERE (c.source_language, c.target_language) IN (('en','fa'), ('en','prs'), ('prs','en'))
ORDER BY c.source_language, c.target_language, c.level, c.title;

\echo ''
\echo '=== AFTER: total course count (sanity — compare with your backup) ==='
SELECT count(*) AS total_courses FROM courses;

-- =====================================================================
-- DRY RUN BY DEFAULT. Change the line below to `COMMIT;` — and only
-- after taking a backup and reviewing the output above — to make the
-- deletions permanent.
-- =====================================================================
ROLLBACK;
