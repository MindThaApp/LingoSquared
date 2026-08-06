export const meta = {
  name: 'content-tier',
  description: 'Graph-run a content tier/unit through review -> fix -> adversarial re-verify; pipelined (no barrier) so item B reviews while item A fixes. Ends by reporting which files are clean and ready for the COORDINATOR to wire into the manifest + commit (the workflow never touches content_manifest.txt or git).',
  phases: [
    { title: 'Author', detail: 'greenfield only — runs when an item sets authored:false' },
    { title: 'Review', detail: 'fresh-context reviewer -> structured findings (SHIP / FIX-FIRST)' },
    { title: 'Fix', detail: 'apply approved fixes, prove 0/0 compile, never mask' },
    { title: 'Verify', detail: 'adversarial skeptic re-reads the files: were fixes real? any masking?' },
  ],
}

// ---- args contract -----------------------------------------------------
// args = {
//   items: [{
//     id: 'en-ru-b2-0508',            // label
//     lang: 'Russian',
//     manifestCourse: 'en-ru-b2',     // course token (coordinator wires this)
//     reviewRealizations: [ ... ],    // the NEW files under review
//     reviewOverlays:     [ ... ],
//     compileRealizations:[ ... ],    // FULL course files for the 0/0 compile check
//     compileOverlays:    [ ... ],    //   (tokens accumulate course-wide)
//     authored: true,                 // false -> run the Author stage first
//     authorBrief: '...'              // optional prompt override for greenfield
//   }],
//   verifyVotes: 1                    // adversarial skeptics per fixed item (economy default 1)
// }
// Returns { report, wireReady }. wireReady = items that are clean & unmasked;
// the coordinator wires those manifest lines and commits (per repo rule, an
// agent must NEVER git-add a manifest line — the shared-manifest footgun).
// ------------------------------------------------------------------------

// args may arrive as an object or a JSON string depending on the caller — tolerate both.
let cfg = args
if (typeof cfg === 'string') { try { cfg = JSON.parse(cfg) } catch (e) { cfg = {} } }
cfg = cfg || {}
const items = cfg.items || []
if (!items.length) { log('content-tier: args.items is empty — nothing to do'); return { report: [], wireReady: [] } }
const verifyVotes = cfg.verifyVotes || 1

const REVIEW_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['verdict', 'findings'],
  properties: {
    verdict: { type: 'string', enum: ['SHIP', 'FIX-FIRST'] },
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['severity', 'file', 'location', 'issue', 'fix'],
        properties: {
          severity: { type: 'string', enum: ['CRITICAL', 'MAJOR', 'MINOR'] },
          file: { type: 'string' },
          location: { type: 'string' },
          issue: { type: 'string' },
          fix: { type: 'string' },
        },
      },
    },
  },
}

const VERIFY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['real', 'masked', 'notes'],
  properties: {
    real: { type: 'boolean' },   // were the claimed fixes ACTUALLY applied & correct
    masked: { type: 'boolean' }, // any degenerate/masked content found
    notes: { type: 'string' },
  },
}

const compileCmd = (item) => {
  const r = (item.compileRealizations || item.reviewRealizations || []).join(' ')
  const o = (item.compileOverlays || item.reviewOverlays || []).join(' ')
  return `.content-venv/bin/python scripts/compile_content.py compile --realization ${r} --overlay ${o} --output /dev/null`
}

const authorPrompt = (item) => item.authorBrief || (
  `You are a content-author sub-agent for /Users/raminazizi/dev/LingoSquared. Author the ${item.lang} tier "${item.id}" ` +
  `following docs/content/AUTHORING_GUIDE.md (all of it) and the shipped nl B2 exemplar for structure/outcome ids. ` +
  `Create ONLY ${(item.reviewRealizations || []).join(', ')} and ${(item.reviewOverlays || []).join(', ')}. ` +
  `Do NOT touch scripts/content_manifest.txt or any existing file. Never mask a validation error — a smaller clean unit beats a padded one. ` +
  `Prove 0 errors/0 warnings and paste output verbatim:\n${compileCmd(item)}`
)

const reviewPrompt = (item) => (
  `You are a FRESH-CONTEXT content reviewer for /Users/raminazizi/dev/LingoSquared. Read the files you review IN FULL.\n` +
  `Review the ${item.lang} tier "${item.id}": realizations ${(item.reviewRealizations || []).join(', ')} + overlays ${(item.reviewOverlays || []).join(', ')}.\n` +
  `Binding standards: docs/content/AUTHORING_GUIDE.md and docs/content/CLAUDE.md.\n\n` +
  `Hunt these known defect classes — each escaped a prior author pass on this project:\n` +
  `- TRANSLATION / reverse_translation items escape author consistency passes: verify accepted-answer variants (incl. transliteration where the script permits), gender/register neutrality, and that the instruction names the exact required forms.\n` +
  `- Model / reading texts must OBEY the grammar the unit itself teaches — flag any rule the text then violates.\n` +
  `- No calques from the Dutch exemplar — the ${item.lang} must read idiomatically from first principles.\n` +
  `- matching_pairs: left = taught ${item.lang} item, right = clue; clue must NEVER contain its own answer; orientation left=taught-vocab. The renderer takes pair display from the REALIZATION only, so a localized/edited clue must not delete the target word.\n` +
  `- Non-Latin scripts (Cyrillic/Arabic/etc.) grade BYTE-STRICT: no distance-1 typo tolerance, no internal-punctuation stripping. Every legitimate learner spelling must be an EXPLICIT accepted answer.\n` +
  `- VALIDATOR-GAMING / masking: reject letter-blank answer-redactions, symbolic (≠ < + →) notation, padding, or an answer smuggled into its own clue. A clean skip beats a masked item.\n\n` +
  `Return structured findings (severity CRITICAL/MAJOR/MINOR; file; location as unit.lesson.exercise; the issue; the EXACT fix). ` +
  `verdict = SHIP only if there are zero CRITICAL and zero MAJOR findings.`
)

const fixPrompt = (item, review) => (
  `You are a content-fix author for /Users/raminazizi/dev/LingoSquared, tier "${item.id}". Apply ONLY these reviewer-approved fixes:\n\n` +
  review.findings.map((f, i) => `${i + 1}. [${f.severity}] ${f.file} ${f.location}: ${f.issue}\n   FIX: ${f.fix}`).join('\n') +
  `\n\nRules: change ONLY what the findings specify, only within ${(item.reviewRealizations || []).join(', ')} and ${(item.reviewOverlays || []).join(', ')}. ` +
  `If any fix is blocked, honestly DROP/skip that item and say so — NEVER mask an error with bogus content, letter-blanks, symbolic notation, or padding. ` +
  `Do NOT touch scripts/content_manifest.txt, git, or any file outside this tier.\n\n` +
  `Prove it — run and paste output verbatim:\n${compileCmd(item)}\nRequired: ZERO errors, ZERO warnings. Report each finding as fixed or dropped-with-reason.`
)

const verifyPrompt = (item, review, i) => (
  `You are an ADVERSARIAL verifier (skeptic #${i + 1}) for /Users/raminazizi/dev/LingoSquared, tier "${item.id}". Default to disbelief.\n` +
  `An author claims these fixes were applied:\n` +
  review.findings.map((f) => `- ${f.location}: ${f.fix}`).join('\n') +
  `\n\nIndependently re-read ${(item.reviewRealizations || []).join(', ')} + ${(item.reviewOverlays || []).join(', ')} and decide:\n` +
  `- real: were the fixes ACTUALLY and correctly applied (not merely claimed)? If uncertain, answer false.\n` +
  `- masked: did the author mask anything with degenerate content — letter-blank redactions, symbolic (≠ < + →) notation, padding, or an answer hidden in its own clue? This class slipped through twice before; look hard. ANY single instance -> masked=true.\n` +
  `Also re-run and confirm 0 errors/0 warnings:\n${compileCmd(item)}`
)

phase('Review')
const results = await pipeline(
  items,
  // Stage 1 — author greenfield tiers only; otherwise pass through untouched.
  async (item) => {
    if (item.authored === false) {
      await agent(authorPrompt(item), { label: `author:${item.id}`, phase: 'Author' })
    }
    return item
  },
  // Stage 2 — fresh-context review.
  async (item) => {
    const review = await agent(reviewPrompt(item), { label: `review:${item.id}`, phase: 'Review', schema: REVIEW_SCHEMA })
    return { item, review }
  },
  // Stage 3 — fix, only if the reviewer found something actionable.
  async ({ item, review }) => {
    const findings = (review && review.findings) || []
    if (!review || review.verdict === 'SHIP' || !findings.length) return { item, review, fixed: false }
    await agent(fixPrompt(item, review), { label: `fix:${item.id}`, phase: 'Fix' })
    return { item, review, fixed: true }
  },
  // Stage 4 — adversarial re-verify, only if we actually changed files.
  async ({ item, review, fixed }) => {
    if (!fixed) return { item, review, fixed, verify: null }
    const checks = (await parallel(
      Array.from({ length: verifyVotes }, (_, i) => () =>
        agent(verifyPrompt(item, review, i), { label: `verify:${item.id}#${i + 1}`, phase: 'Verify', schema: VERIFY_SCHEMA })),
    )).filter(Boolean)
    const masked = checks.some((v) => v.masked)
    const allReal = checks.length > 0 && checks.every((v) => v.real)
    return { item, review, fixed, verify: { masked, allReal, checks } }
  },
)

const report = results.filter(Boolean).map((r) => {
  const shipped = r.review && r.review.verdict === 'SHIP'
  const clean = r.verify ? (r.verify.allReal && !r.verify.masked) : !!shipped
  return {
    id: r.item.id,
    manifestCourse: r.item.manifestCourse,
    verdict: r.review && r.review.verdict,
    findings: r.review ? ((r.review.findings || []).length) : 0,
    fixed: r.fixed,
    masked: r.verify ? r.verify.masked : false,
    clean,
    realizations: r.item.reviewRealizations,
    overlays: r.item.reviewOverlays,
  }
})

const wireReady = report.filter((x) => x.clean && !x.masked)
log(`content-tier done: ${wireReady.length}/${report.length} clean & ready for the coordinator to wire+commit`)
if (report.some((x) => x.masked)) log('WARNING: masking detected on one or more items — do NOT wire those; re-review.')
return { report, wireReady }
