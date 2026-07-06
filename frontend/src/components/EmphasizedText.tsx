// Explanatory text (a teaching card's `note`, an exercise's `feedback`)
// often mixes the target language inline with the source-language
// sentence explaining it, e.g. "*Om ... te* + infinitive expresses
// purpose; *me in te schrijven* splits the separable verb." With no
// visual distinction, a learner can't tell which words are the language
// they're learning and which are the explanation. Content authors mark
// target-language spans with single asterisks (`*...*`, the same
// convention as Markdown italics); this component parses that and
// renders the marked spans emphasized. Plain text with no asterisks
// renders unchanged, so this is a strict additive convention -- existing
// un-marked note/feedback strings are unaffected until content is
// updated to use it.
export function EmphasizedText({ text }: { text: string }) {
  const parts = text.split(/\*([^*]+)\*/g);
  // String.split with a single capturing group alternates
  // [unmatched, matched, unmatched, matched, ...]; odd indices are the
  // asterisk-wrapped (target-language) spans.
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <em className="target-language-span" key={i}>
            {part}
          </em>
        ) : (
          part
        ),
      )}
    </>
  );
}
