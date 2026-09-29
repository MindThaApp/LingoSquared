import ast
import importlib.util
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_content_compiler():
    path = Path(__file__).resolve().parents[1] / "compile_content.py"
    spec = importlib.util.spec_from_file_location(
        "lingosquared_compile_content",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unit_track_validation_accepts_situation_and_rejects_unknown_values():
    compiler = load_content_compiler()
    accepted = compiler.Report()
    compiler.validate_unit_tracks({"units": [{"track": "situation"}]}, accepted)
    assert accepted.errors == []

    rejected = compiler.Report()
    compiler.validate_unit_tracks({"units": [{"track": "optional"}]}, rejected)
    assert len(rejected.errors) == 1
    assert "realization.units[0].track" in rejected.errors[0]

    compiled = compiler.compile_import_request(
        {
            "target_language": "es",
            "cefr_level": "A1",
            "units": [{"content_key": "es.a1.unit01", "track": "situation", "lessons": []}],
        },
        {"source_language": "en", "target_language": "es", "course": {"title": "Test"}},
    )
    assert compiled["courses"][0]["units"][0]["track"] == "situation"
    assert "track" not in compiler.compile_import_request(
        {
            "target_language": "es",
            "cefr_level": "A1",
            "units": [{"content_key": "es.a1.unit01", "lessons": []}],
        },
        {"source_language": "en", "target_language": "es", "course": {"title": "Test"}},
    )["courses"][0]["units"][0]


def test_compiler_preserves_all_accepted_variants_and_canonical_value():
    compiler = load_content_compiler()

    compiled = compiler.canonical_response(
        {
            "accepted_answers": [
                {"value": "salam", "status": "correct"},
                {"value": "salâm", "status": "correct"},
                {"value": "salām", "status": "correct"},
                {
                    "value": "salaam",
                    "status": "acceptable_with_note",
                    "note": "Common English-oriented spelling.",
                },
            ]
        }
    )

    assert compiled == {
        "canonical": "salam",
        "accepted": ["salam", "salâm", "salām", "salaam"],
    }


def test_compiler_keeps_existing_single_and_structured_answer_shapes():
    compiler = load_content_compiler()

    assert compiler.canonical_response(
        {
            "accepted_answers": [
                {
                    "value": ["Good", "afternoon"],
                    "status": "correct",
                }
            ]
        }
    ) == ["Good", "afternoon"]

    mapping = {"س": "s", "ل": "l"}
    assert compiler.canonical_response(
        {
            "accepted_answers": [
                {
                    "value": mapping,
                    "status": "correct",
                }
            ]
        }
    ) == mapping

    assert compiler.canonical_response(
        {"correct_response": ["Cómo", "está", "usted"]}
    ) == ["Cómo", "está", "usted"]


def practice_pack(**template_overrides):
    template = {
        "content_key": "practice.en-fa.test.greeting.001",
        "lesson_content_key": "fa.a1.unit01.lesson02.everyday_greetings",
        "type": "multiple_choice",
        "frame": {
            "text": "{greeting}",
            "language_code": "fa",
            "direction": "rtl",
        },
        "slots": {
            "greeting": {
                "language_code": "fa",
                "part_of_speech": "phrase",
                "agreement_tags": {"function": "greeting"},
            }
        },
        "answer_derivation": {"kind": "slot_gloss", "slot": "greeting"},
        "feedback_frame": {
            "text": "{greeting} is the reviewed greeting.",
            "language_code": "en",
            "direction": "ltr",
        },
    }
    template.update(template_overrides)
    return {
        "schema_version": "1.0",
        "pack_key": "practice.en-fa.a1.unit01",
        "source_language": "en",
        "target_language": "fa",
        "unit_content_key": "fa.a1.unit01.greetings",
        "tag_schema": {
            "part_of_speech": ["phrase"],
            "agreement_tags": {"function": ["greeting"]},
        },
        "templates": [template],
    }


def test_practice_compiler_rejects_unsupported_exercise_type(tmp_path):
    compiler = load_content_compiler()
    pack = practice_pack(type="writing_prompt")

    report = compiler.validate_practice_packs([(tmp_path / "pack.yaml", pack)])

    assert any("is not supported" in error for error in report.errors)


def test_practice_compiler_rejects_unknown_constraint_tag(tmp_path):
    compiler = load_content_compiler()
    pack = practice_pack()
    pack["templates"][0]["slots"]["greeting"]["agreement_tags"] = {
        "register": "formal"
    }

    report = compiler.validate_practice_packs([(tmp_path / "pack.yaml", pack)])

    assert any("undeclared agreement tag" in error for error in report.errors)


def test_practice_compiler_detects_existing_content_key_collision(tmp_path):
    compiler = load_content_compiler()
    pack = practice_pack(content_key="fa.a1.existing")
    existing = {"lesson": {"content_key": "fa.a1.existing"}}

    report = compiler.validate_practice_packs(
        [(tmp_path / "pack.yaml", pack)],
        [(tmp_path / "realization.yaml", existing)],
    )
    assert any("duplicate content_key" in error for error in report.errors)


def test_a1_free_text_word_bank_and_skip_rules():
    compiler = load_content_compiler()
    def compile_one(level, value):
        item = {"type": "translation", "content_key": "en.fa.a1.lesson.item"}
        overlay = {"accepted_answers": [{"value": value, "status": "correct"}]}
        choices = compiler.compile_exercise(
            item, overlay, 1, "en", "en", content_key=item["content_key"],
            cefr_level=level,
            distractor_tokens=["station", "garden", "morning", "quickly", "blue"],
        )
        return choices["prompt"].get("word_bank")

    bank = compile_one("A1", "Hello, world!")
    assert bank[:2] == ["Hello", "world"]
    assert len(bank) >= 2
    assert compile_one("B1", "Hello world") is None
    assert compile_one("A1", " ".join(["word"] * 13)) is None
    assert compile_one("A1", "Hello world")[:2] == ["Hello", "world"]


def test_long_word_order_keeps_authored_word_bank_unchanged():
    compiler = load_content_compiler()
    authored_bank = ["First,", "second", "tile?", *[f"word{i}" for i in range(11)]]
    exercise = {
        "type": "word_order",
        "content_key": "long-authored-order",
        "word_bank": authored_bank,
    }
    compiled = compiler.compile_exercise(
        exercise,
        {"accepted_answers": [{"value": "one two three", "status": "correct"}]},
        1,
        "en",
        "fa",
        content_key=exercise["content_key"],
        cefr_level="A1",
        introduced_tokens={"first", "second"},
    )

    assert compiled["prompt"]["word_bank"] == authored_bank


def test_word_bank_language_script_letter_and_short_answer_filters():
    compiler = load_content_compiler()

    def bank(value, target="nl", answer_language=None, candidates=(), lexicon=None):
        item = {"type": "translation", "content_key": "filter-case"}
        overlay = {"accepted_answers": [{"value": value, "status": "correct"}]}
        if answer_language:
            overlay["answer_language_code"] = answer_language
        return compiler.compile_exercise(
            item, overlay, 1, "en", target, content_key="filter-case",
            cefr_level="A1", distractor_tokens=list(candidates),
            introduced_tokens=lexicon or {*compiler.tokenize(value), *(
                str(token).casefold() for token, _ in candidates
                if isinstance(token, str)
            )},
        )["prompt"].get("word_bank")

    # English answer-language material cannot leak into a Dutch bank; this
    # mirrors "Good" and the A2 "suit"/"Would" failures.
    dutch = bank("Hoe gaat het", candidates=[("Goed", "nl"), ("Good", "en")])
    assert "Goed" in dutch and "Good" not in dutch
    assert bank("Goed, dank u", candidates=[("suit", "en"), ("Would", "en")]) == [
        "Goed", "dank", "u"
    ]

    # Latin transliteration into fa is skipped; Arabic-script banks cannot
    # contain single letters, including letters collected from drills.
    assert bank("salam", target="fa", candidates=[("سلام", "fa")]) is None
    persian = bank("سلام دنیا", target="fa", candidates=[
        ("س", "fa"), ("ل", "fa"), ("چ", "fa"), ("yes", "fa"),
    ], lexicon={"سلام", "دنیا"})
    assert persian == ["سلام", "دنیا"]
    dutch_short_word = bank("ik heb", candidates=[("u", "nl")], lexicon={"ik", "heb", "u"})
    assert "u" in dutch_short_word
    assert bank("سلام", target="prs", candidates=[("س", "prs"), ("yes", "prs")]) is None


def test_word_bank_excludes_other_accepted_answers_and_is_deterministic():
    compiler = load_content_compiler()
    exercise = {"type": "writing_prompt", "content_key": "stable-key"}
    overlay = {"accepted_answers": [
        {"value": "Cats sleep", "status": "correct"},
        {"value": "Dogs sleep", "status": "correct"},
    ]}
    def run():
        return compiler.compile_exercise(
            exercise, overlay, 1, "en", "es", content_key="stable-key",
            cefr_level="A2", distractor_tokens=["Cats", "Dogs", "sun", "rain", "tree"],
            introduced_tokens={"cats", "sleep", "sun", "rain", "tree"},
        )["prompt"]["word_bank"]
    first, second = run(), run()
    assert first == second
    assert "Cats" in first and "sleep" in first
    assert "Dogs" not in first


def test_word_bank_requires_course_taught_tokens_and_strips_unicode_punctuation():
    compiler = load_content_compiler()
    exercise = {"type": "translation", "content_key": "lexicon-case"}

    def bank(value, answer_language, candidates, lexicon):
        overlay = {
            "answer_language_code": answer_language,
            "accepted_answers": [{"value": value, "status": "correct"}],
        }
        return compiler.compile_exercise(
            exercise, overlay, 1, "en", answer_language, content_key="lexicon-case",
            cefr_level="A1", distractor_tokens=candidates,
            introduced_tokens=lexicon,
        )["prompt"].get("word_bank")

    # An English answer item can carry Latin-script tokens, but only taught
    # Dutch tokens from Dutch-answer items may enter this bank.
    dutch = bank("ik heb", "nl", [
        ("cat", "en"), ("dog", "en"), ("kat", "nl"), ("hond", "nl"),
        ], {"ik", "heb", "kat", "hond"})
    assert dutch[:2] == ["ik", "heb"]
    assert set(dutch[2:]) <= {"kat", "hond"}
    assert not ({"cat", "dog"} & set(dutch))

    persian = bank("است؟ باشه،", "fa", [("کتاب؟", "fa")], {
        "است", "باشه", "کتاب",
    })
    assert "است" in persian and "باشه" in persian
    assert "است؟" not in persian and "باشه،" not in persian
    assert "کتاب" in persian and "کتاب؟" not in persian


def test_compile_forwards_optional_course_recommended():
    compiler = load_content_compiler()
    realization = {"target_language": "es", "cefr_level": "A1", "units": []}
    overlay = {"source_language": "en", "course": {"title": "Spanish", "recommended": True}}
    assert compiler.compile_import_request(realization, overlay)["courses"][0]["recommended"] is True
    overlay["course"].pop("recommended")
    assert "recommended" not in compiler.compile_import_request(realization, overlay)["courses"][0]

def test_practice_compiler_emits_stable_self_describing_artifact(tmp_path):
    compiler = load_content_compiler()
    pack = practice_pack()
    report = compiler.validate_practice_packs([(tmp_path / "pack.yaml", pack)])

    assert report.errors == []
    compiled = compiler.compile_practice_packs([pack])
    assert compiled["artifact_type"] == "lingosquared.practice_templates"
    assert compiled["artifact_version"] == 1
    assert compiled["source_language"] == "en"
    assert compiled["target_language"] == "fa"
    assert compiled["packs"][0]["templates"][0]["slots"] == pack["templates"][0]["slots"]


def test_compiler_rejects_single_block_labelled_dialogue():
    compiler = load_content_compiler()
    content_key = "es.a1.lesson01.teach.dialogue"

    with pytest.raises(ValueError, match=content_key):
        compiler.compile_teaching_item(
            {
                "content_key": content_key,
                "kind": "dialogue",
                "target": {
                    "text": "Elena: Hola.\nMateo: Buenos días.",
                    "language_code": "es",
                    "direction": "ltr",
                },
            },
            {},
            "en",
        )


def test_compiler_emits_reading_glosses_only_when_authored():
    compiler = load_content_compiler()
    item = {
        "content_key": "nl.b1.lesson01.teach.reading",
        "kind": "reading",
        "target": {
            "text": "Kasia verandert van baan.",
            "language_code": "nl",
            "direction": "ltr",
        },
    }

    without_glosses = compiler.compile_teaching_item(item, {}, "en")
    with_glosses = compiler.compile_teaching_item(
        item,
        {"glosses": {"verandert": "changes", "baan": "job"}},
        "en",
    )

    assert "glosses" not in without_glosses
    assert with_glosses["glosses"] == {
        "verandert": "changes",
        "baan": "job",
    }


def test_reading_gloss_validator_warns_for_token_absent_from_passage():
    compiler = load_content_compiler()
    realization = {
        "target_language": "nl",
        "units": [{"lessons": [{"teaching": [{
            "content_key": "nl.b1.lesson01.teach.reading",
            "kind": "reading",
            "target": {"text": "Kasia verandert van baan."},
        }]}]}],
    }
    overlay = {
        "teaching": {
            "nl.b1.lesson01.teach.reading": {
                "glosses": {"verandert": "changes", "ban": "job"},
            }
        }
    }
    report = compiler.Report()

    compiler.validate_reading_glosses(realization, overlay, report)

    assert len(report.warnings) == 1
    assert "'ban' is not a whole-word token" in report.warnings[0]


def test_reading_tokenizer_keeps_internal_joiners_without_changing_global_tokenizer():
    compiler = load_content_compiler()
    text = "Collega's d'r co-op नमस्ते"

    assert compiler.tokenize_reading(text) == {
        "collega's",
        "d'r",
        "co-op",
        "नमस्ते",
    }
    assert compiler.tokenize(text) == {
        "collega",
        "s",
        "d",
        "r",
        "co",
        "op",
        "नमस्ते",
    }


def test_compiler_accepts_split_dialogue_turns_with_speakers():
    compiler = load_content_compiler()

    compiler.validate_dialogue_teaching_card(
        {
            "kind": "dialogue",
            "text_blocks": [
                {
                    "speaker": "Elena",
                    "text": "Hola.",
                    "language_code": "es",
                    "direction": "ltr",
                },
                {
                    "speaker": "Mateo",
                    "text": "Buenos días.",
                    "language_code": "es",
                    "direction": "ltr",
                },
            ],
        },
        "es.a1.lesson01.teach.dialogue",
    )


def audio_distractor_realization():
    return {
        "target_language": "en",
        "media_assets": [
            {
                "content_key": "en.test.audio.dialogue.01",
                "text": (
                    "Mia: I booked the early train. Daniel: Great, I will "
                    "bring the tickets. Mia: Please meet me at platform two."
                ),
            }
        ],
        "units": [
            {
                "lessons": [
                    {
                        "exercises": [
                            {
                                "content_key": "en.test.exercise.listen_train",
                                "type": "listen_select",
                                "tested_text": "Please meet me at platform two",
                                "media_asset_key": "en.test.audio.dialogue.01",
                            }
                        ]
                    }
                ]
            }
        ],
    }


def test_audio_distractor_validator_rejects_tested_speaker_line():
    compiler = load_content_compiler()
    report = compiler.Report()

    compiler.validate_audio_distractors_not_heard_by_tested_speaker(
        audio_distractor_realization(),
        {
            "exercises": {
                "en.test.exercise.listen_train": {
                    "correct_option": "Please meet me at platform two",
                    "distractors": [
                        "I booked the early train",
                        "The train leaves late",
                    ],
                }
            }
        },
        report,
    )

    assert any(
        "I booked the early train" in error
        and "tested speaker says anywhere in that audio" in error
        for error in report.errors
    )


def test_audio_distractor_validator_accepts_unheard_fixed_distractor():
    compiler = load_content_compiler()
    report = compiler.Report()

    compiler.validate_audio_distractors_not_heard_by_tested_speaker(
        audio_distractor_realization(),
        {
            "exercises": {
                "en.test.exercise.listen_train": {
                    "correct_option": "Please meet me at platform two",
                    "distractors": [
                        "The train leaves late",
                        "The station is closed",
                    ],
                }
            }
        },
        report,
    )

    assert report.errors == []
    assert report.warnings == []


def dictation_documents(tested_text, asset_text, correct_response):
    content_key = "de.test.exercise.dictation_bank"
    return (
        {
            "target_language": "de",
            "media_assets": [
                {
                    "content_key": "de.test.audio.bank",
                    "script": asset_text,
                }
            ],
            "units": [
                {
                    "lessons": [
                        {
                            "exercises": [
                                {
                                    "content_key": content_key,
                                    "type": "dictation",
                                    "tested_text": tested_text,
                                    "media_asset_key": "de.test.audio.bank",
                                }
                            ]
                        }
                    ]
                }
            ],
        },
        {
            "exercises": {
                content_key: {"correct_response": correct_response}
            }
        },
    )


def test_dictation_byte_equality_validator_accepts_boundary_punctuation_difference():
    compiler = load_content_compiler()
    realization, overlay = dictation_documents(
        "مرحبًا",
        "مرحبًا،",
        "مرحبًا",
    )
    report = compiler.Report()

    compiler.validate_dictation_byte_equality(realization, overlay, report)

    assert report.errors == []
    assert report.warnings == []


@pytest.mark.parametrize(
    ("tested_text", "asset_text", "correct_response"),
    [
        ("...", "!!!", "..."),
        ("", "...", ""),
    ],
)
def test_dictation_byte_equality_validator_does_not_tolerate_empty_normalization(
    tested_text,
    asset_text,
    correct_response,
):
    compiler = load_content_compiler()
    realization, overlay = dictation_documents(
        tested_text,
        asset_text,
        correct_response,
    )
    report = compiler.Report()

    compiler.validate_dictation_byte_equality(realization, overlay, report)

    assert report.errors == []
    assert len(report.warnings) == 1


def test_dictation_byte_equality_validator_warns_on_internal_punctuation_difference():
    compiler = load_content_compiler()
    realization, overlay = dictation_documents(
        "Ja ich komme.",
        "Ja, ich komme.",
        "Ja ich komme",
    )
    report = compiler.Report()

    compiler.validate_dictation_byte_equality(realization, overlay, report)

    assert report.errors == []
    assert len(report.warnings) == 1
    warning = report.warnings[0]
    assert "de.test.exercise.dictation_bank" in warning
    assert "tested_text 'Ja ich komme.' (UTF-8 b'Ja ich komme.')" in warning
    assert (
        "media asset 'de.test.audio.bank' script "
        "'Ja, ich komme.' (UTF-8 b'Ja, ich komme.')" in warning
    )


def test_dictation_byte_equality_validator_accepts_identical_bytes():
    compiler = load_content_compiler()
    realization, overlay = dictation_documents(
        "Wo ist die Bank?",
        "Wo ist die Bank?",
        "Wo ist die Bank?",
    )
    report = compiler.Report()

    compiler.validate_dictation_byte_equality(realization, overlay, report)

    assert report.errors == []
    assert report.warnings == []


def german_typed_documents(accepted_answers, exercise_type="writing_prompt"):
    content_key = "de.test.exercise.write_umlauts"
    return (
        {
            "target_language": "de",
            "units": [
                {
                    "lessons": [
                        {
                            "exercises": [
                                {
                                    "content_key": content_key,
                                    "type": exercise_type,
                                }
                            ]
                        }
                    ]
                }
            ],
        },
        {"exercises": {content_key: {"accepted_answers": accepted_answers}}},
    )


def test_german_transliteration_validator_warns_with_missing_variant():
    compiler = load_content_compiler()
    realization, overlay = german_typed_documents(
        [{"value": "Ärger über Größe und Öl", "status": "correct"}]
    )
    report = compiler.Report()

    compiler.validate_german_transliteration_variants(
        realization,
        overlay,
        report,
    )

    assert report.errors == []
    assert len(report.warnings) == 1
    warning = report.warnings[0]
    assert "de.test.exercise.write_umlauts" in warning
    assert "missing accepted variant 'Aerger ueber Groesse und Oel'" in warning


def test_german_transliteration_validator_accepts_full_variant():
    compiler = load_content_compiler()
    realization, overlay = german_typed_documents(
        [
            {"value": "Ärger über Größe und Öl", "status": "correct"},
            {
                "value": "Aerger ueber Groesse und Oel",
                "status": "acceptable_with_note",
            },
        ]
    )
    report = compiler.Report()

    compiler.validate_german_transliteration_variants(
        realization,
        overlay,
        report,
    )

    assert report.errors == []
    assert report.warnings == []


def test_german_transliteration_validator_warns_on_translation_missing_variant():
    compiler = load_content_compiler()
    realization, overlay = german_typed_documents(
        [{"value": "Ärger über Größe und Öl", "status": "correct"}],
        exercise_type="translation",
    )
    report = compiler.Report()

    compiler.validate_german_transliteration_variants(
        realization,
        overlay,
        report,
    )

    assert report.errors == []
    assert len(report.warnings) == 1
    warning = report.warnings[0]
    assert "de.test.exercise.write_umlauts" in warning
    assert "missing accepted variant 'Aerger ueber Groesse und Oel'" in warning


def test_german_transliteration_validator_accepts_translation_full_variant():
    compiler = load_content_compiler()
    realization, overlay = german_typed_documents(
        [
            {"value": "Ärger über Größe und Öl", "status": "correct"},
            {
                "value": "Aerger ueber Groesse und Oel",
                "status": "acceptable_with_note",
            },
        ],
        exercise_type="translation",
    )
    report = compiler.Report()

    compiler.validate_german_transliteration_variants(
        realization,
        overlay,
        report,
    )

    assert report.errors == []
    assert report.warnings == []


def test_german_transliteration_validator_ignores_dictation():
    """dictation stays orthography-strict by explicit content policy - it
    must never be flagged for a missing ASCII transliteration variant, even
    though grade()'s dictation branch would honor one if present."""
    compiler = load_content_compiler()
    realization, overlay = german_typed_documents(
        [{"value": "Ärger über Größe und Öl", "status": "correct"}],
        exercise_type="dictation",
    )
    report = compiler.Report()

    compiler.validate_german_transliteration_variants(
        realization,
        overlay,
        report,
    )

    assert report.errors == []
    assert report.warnings == []


def test_audio_distractor_validator_warns_on_different_speaker_line():
    compiler = load_content_compiler()
    report = compiler.Report()
    realization = audio_distractor_realization()
    realization["units"][0]["lessons"][0]["exercises"][0][
        "type"
    ] = "dialogue_response"

    compiler.validate_audio_distractors_not_heard_by_tested_speaker(
        realization,
        {
            "exercises": {
                "en.test.exercise.listen_train": {
                    "correct_option": "Please meet me at platform two",
                    "distractors": ["Great, I will bring the tickets"],
                }
            }
        },
        report,
    )

    assert report.errors == []
    assert any(
        "different speaker from the tested speaker" in warning
        for warning in report.warnings
    )


def test_audio_distractor_validator_rejects_unlabelled_heard_words():
    compiler = load_content_compiler()
    report = compiler.Report()

    realization = {
        "target_language": "de",
        "media_assets": [
            {
                "content_key": "de.test.audio.word_list",
                "text": "aufstehen, frühstücken, arbeiten, lernen, schlafen",
            }
        ],
        "units": [
            {
                "lessons": [
                    {
                        "exercises": [
                            {
                                "content_key": "de.test.exercise.listen_activities",
                                "type": "listen_select",
                                "tested_text": "arbeiten",
                                "media_asset_key": "de.test.audio.word_list",
                            }
                        ]
                    }
                ]
            }
        ],
    }

    compiler.validate_audio_distractors_not_heard_by_tested_speaker(
        realization,
        {
            "exercises": {
                "de.test.exercise.listen_activities": {
                    "correct_option": "arbeiten",
                    "distractors": ["aufstehen", "lernen"],
                }
            }
        },
        report,
    )

    assert any(
        "aufstehen" in error and "unlabelled media asset" in error
        for error in report.errors
    )


def test_audio_distractor_validator_rejects_dialogue_comprehension_speaker_line():
    compiler = load_content_compiler()
    report = compiler.Report()
    realization = audio_distractor_realization()
    realization["units"][0]["lessons"][0]["exercises"][0][
        "type"
    ] = "dialogue_comprehension"

    compiler.validate_audio_distractors_not_heard_by_tested_speaker(
        realization,
        {
            "exercises": {
                "en.test.exercise.listen_train": {
                    "correct_option": "Please meet me at platform two",
                    "distractors": [
                        "I booked the early train",
                        "The train leaves late",
                    ],
                }
            }
        },
        report,
    )

    assert any(
        "I booked the early train" in error
        and "dialogue_comprehension" in error
        and "tested speaker says anywhere in that audio" in error
        for error in report.errors
    )


def test_dialogue_comprehension_compiles_asset_transcript_and_warns_when_missing():
    compiler = load_content_compiler()
    text = "Lotte: Hoi, ik ben Lotte."
    exercise = {
        "content_key": "nl.test.exercise.dialogue",
        "type": "dialogue_comprehension",
        "tested_text": ["Lotte", "name"],
        "media_asset_key": "nl.test.audio.dialogue",
    }
    assets = {"nl.test.audio.dialogue": {"text": text}}

    compiled = compiler.compile_exercise(
        exercise,
        {"accepted_answers": [{"value": "Lotte", "status": "correct"}]},
        1,
        "en",
        "nl",
        media_assets=assets,
    )
    assert compiled["prompt"]["audio_text"] == text
    assert compiled["prompt"]["audio_language_code"] == "nl"

    realization = {
        "units": [{"lessons": [{"exercises": [exercise]}]}],
        "media_assets": [],
    }
    report = compiler.Report()
    compiler.validate_dialogue_comprehension_audio(realization, report)
    without_asset = compiler.compile_exercise(
        exercise,
        {"accepted_answers": [{"value": "Lotte", "status": "correct"}]},
        1,
        "en",
        "nl",
    )
    assert "audio_text" not in without_asset["prompt"]
    assert "audio_language_code" not in without_asset["prompt"]
    assert len(report.warnings) == 1
    assert "dialogue_comprehension media asset" in report.warnings[0]


def test_listen_select_compile_audio_behavior_is_unchanged():
    compiler = load_content_compiler()
    exercise = {
        "type": "listen_select",
        "tested_text": "Hallo",
        "media_asset_key": "nl.test.audio.greeting",
    }
    compiled = compiler.compile_exercise(
        exercise,
        {"accepted_answers": [{"value": "Hallo", "status": "correct"}]},
        1,
        "en",
        "nl",
        media_assets={"nl.test.audio.greeting": {"text": "Asset transcript"}},
    )
    assert compiled["prompt"]["audio_text"] == "Hallo"
    assert compiled["prompt"]["audio_language_code"] == "nl"


def test_option_correct_option_must_be_in_accepted_answers():
    # The grader is punctuation-sensitive, so a displayed correct_option that
    # is not itself among the accepted_answers means a learner who picks the
    # visible correct option is graded wrong. validate_option_accepted_answers_
    # are_displayed (rewritten in 9e5ca493 to mirror that grader) must flag it.
    compiler = load_content_compiler()
    report = compiler.Report()

    realization = {
        "target_language": "de",
        "units": [
            {
                "lessons": [
                    {
                        "exercises": [
                            {
                                "content_key": "de.test.exercise.listen_time",
                                "type": "dialogue_comprehension",
                            }
                        ]
                    }
                ]
            }
        ],
    }

    compiler.validate_option_accepted_answers_are_displayed(
        realization,
        {
            "exercises": {
                "de.test.exercise.listen_time": {
                    "correct_option": "um sieben Uhr",
                    "distractors": ["um zehn Uhr", "am Nachmittag"],
                    "accepted_answers": [
                        {"value": "Ich stehe um sieben Uhr auf"},
                    ],
                }
            }
        },
        report,
    )

    assert any(
        "um sieben Uhr" in error
        and "does not include the displayed correct_option" in error
        for error in report.errors
    )


# ---------------------------------------------------------------------------
# Backend-constraint mirrors: teaching `kind`, exercise `type`, VARCHAR widths.
#
# Each of these three validators exists because the compiler used to pass
# content the backend then rejected (a 422 on import for kind/type, a 500 at
# the Postgres layer for over-length titles). The `*_match_backend_*` tests
# below read the backend definitions directly, so the next time somebody adds
# an ExerciseType member or a teaching kind without updating the compiler,
# these fail instead of the drift being discovered by a broken import.
# ---------------------------------------------------------------------------


def _backend_literal_values(class_name: str, field: str) -> set[str]:
    source = (REPO_ROOT / "backend/app/schemas/api.py").read_text(
        encoding="utf-8"
    )
    match = re.search(
        rf"class {class_name}\([^)]*\):\s*.*?\b{field}\s*:\s*Literal\[([^\]]+)\]",
        source,
    )
    assert match is not None, (
        f"could not find {class_name}.{field} Literal in "
        "backend/app/schemas/api.py -- the mirror comment in "
        "scripts/compile_content.py needs re-pointing"
    )
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def _backend_entities_tree() -> ast.Module:
    return ast.parse(
        (REPO_ROOT / "backend/app/models/entities.py").read_text(
            encoding="utf-8"
        )
    )


def _backend_enum_values(enum_name: str) -> set[str]:
    for node in ast.walk(_backend_entities_tree()):
        if isinstance(node, ast.ClassDef) and node.name == enum_name:
            return {
                statement.value.value
                for statement in node.body
                if isinstance(statement, ast.Assign)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            }
    raise AssertionError(
        f"could not find enum {enum_name} in backend/app/models/entities.py"
    )


def _backend_varchar_width(class_name: str, column: str) -> int:
    for node in ast.walk(_backend_entities_tree()):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for statement in node.body:
            if (
                not isinstance(statement, ast.AnnAssign)
                or not isinstance(statement.target, ast.Name)
                or statement.target.id != column
                or not isinstance(statement.value, ast.Call)
            ):
                continue
            for argument in statement.value.args:
                if (
                    isinstance(argument, ast.Call)
                    and isinstance(argument.func, ast.Name)
                    and argument.func.id == "String"
                    and argument.args
                    and isinstance(argument.args[0], ast.Constant)
                ):
                    return argument.args[0].value
    raise AssertionError(
        f"could not find a String(n) width for {class_name}.{column} in "
        "backend/app/models/entities.py"
    )


def teaching_kind_realization(kind):
    card = {
        "content_key": "ru.b1.unit40.lesson02.teach.grammar_note",
        "target": {
            "text": "хотя + придаточное",
            "language_code": "ru",
            "direction": "ltr",
        },
    }
    if kind is not None:
        card["kind"] = kind
    return {
        "target_language": "ru",
        "units": [
            {
                "content_key": "ru.b1.unit40.rasskaz",
                "title": "Рассказ",
                "lessons": [
                    {
                        "content_key": "ru.b1.unit40.lesson02",
                        "title": "Связки",
                        "teaching": [card],
                    }
                ],
            }
        ],
    }


def test_teaching_kind_validator_rejects_the_ru_b1_grammar_kind():
    compiler = load_content_compiler()
    report = compiler.Report()

    compiler.validate_teaching_kinds(
        teaching_kind_realization("grammar"),
        report,
    )

    assert any(
        "realization.units[0].lessons[0].teaching[0].kind" in error
        and "'grammar' is not a valid teaching card kind" in error
        for error in report.errors
    )


def test_teaching_kind_validator_rejects_missing_and_non_string_kind():
    compiler = load_content_compiler()

    missing_report = compiler.Report()
    compiler.validate_teaching_kinds(
        teaching_kind_realization(None),
        missing_report,
    )
    assert any(
        "teaching card has no kind" in error
        for error in missing_report.errors
    )

    # A bare `kind: yes` in YAML parses as a bool, not a string -- the same
    # boolean-coercion class validate_no_stray_yaml_booleans guards elsewhere.
    boolean_report = compiler.Report()
    compiler.validate_teaching_kinds(
        teaching_kind_realization(True),
        boolean_report,
    )
    assert any(
        "must be a string" in error for error in boolean_report.errors
    )


def test_teaching_kind_validator_accepts_every_valid_kind():
    compiler = load_content_compiler()

    for kind in sorted(compiler.VALID_TEACHING_KINDS):
        report = compiler.Report()
        compiler.validate_teaching_kinds(
            teaching_kind_realization(kind),
            report,
        )
        assert report.errors == [], f"{kind!r} should be accepted"
        assert report.warnings == []


def test_compiler_teaching_kinds_match_the_backend_import_schema():
    compiler = load_content_compiler()

    assert compiler.VALID_TEACHING_KINDS == _backend_literal_values(
        "TeachingCard", "kind"
    )
    assert compiler.VALID_TEACHING_KINDS == _backend_literal_values(
        "ContentItemImport", "kind"
    )


def exercise_type_realization(exercise_type):
    exercise = {"content_key": "ru.b1.unit40.lesson02.exercise01.order"}
    if exercise_type is not None:
        exercise["type"] = exercise_type
    return {
        "target_language": "ru",
        "units": [
            {
                "content_key": "ru.b1.unit40.rasskaz",
                "title": "Рассказ",
                "lessons": [
                    {
                        "content_key": "ru.b1.unit40.lesson02",
                        "title": "Связки",
                        "exercises": [exercise],
                    }
                ],
            }
        ],
    }


def test_exercise_type_validator_rejects_unknown_type():
    compiler = load_content_compiler()
    report = compiler.Report()

    compiler.validate_exercise_types(
        exercise_type_realization("word_ordering"),
        report,
    )

    assert any(
        "realization.units[0].lessons[0].exercises[0].type" in error
        and "'word_ordering' is not a valid exercise type" in error
        for error in report.errors
    )


def test_exercise_type_validator_rejects_missing_type():
    compiler = load_content_compiler()
    report = compiler.Report()

    compiler.validate_exercise_types(
        exercise_type_realization(None),
        report,
    )

    assert any("exercise has no type" in error for error in report.errors)


def test_exercise_type_validator_accepts_every_valid_type():
    compiler = load_content_compiler()

    for exercise_type in sorted(compiler.VALID_EXERCISE_TYPES):
        report = compiler.Report()
        compiler.validate_exercise_types(
            exercise_type_realization(exercise_type),
            report,
        )
        assert report.errors == [], f"{exercise_type!r} should be accepted"
        assert report.warnings == []


def test_compiler_exercise_types_match_the_backend_enum():
    compiler = load_content_compiler()

    assert compiler.VALID_EXERCISE_TYPES == _backend_enum_values(
        "ExerciseType"
    )
    # The practice-pack whitelist is a deliberate subset, not a rival list.
    assert compiler.PRACTICE_EXERCISE_TYPES < compiler.VALID_EXERCISE_TYPES


def length_documents(
    course_title="Russian B1",
    unit_title="Рассказ",
    lesson_title="Связки",
    teaching_title="Contrast connectors",
    teaching_key="ru.b1.unit40.lesson02.teach.hotja",
    exercise_key="ru.b1.unit40.lesson02.exercise01.order",
    overlay_unit_title=None,
    overlay_lesson_title=None,
):
    realization = {
        "target_language": "ru",
        "units": [
            {
                "content_key": "ru.b1.unit40.rasskaz",
                "title": unit_title,
                "lessons": [
                    {
                        "content_key": "ru.b1.unit40.lesson02",
                        "title": lesson_title,
                        "teaching": [
                            {
                                "content_key": teaching_key,
                                "kind": "grammar_note",
                                "target": {
                                    "text": "хотя",
                                    "language_code": "ru",
                                    "direction": "ltr",
                                },
                            }
                        ],
                        "exercises": [
                            {
                                "content_key": exercise_key,
                                "type": "word_order",
                            }
                        ],
                    }
                ],
            }
        ],
    }
    overlay = {
        "source_language": "en",
        "target_language": "ru",
        "course": {"title": course_title},
        "teaching": {teaching_key: {"title": teaching_title}},
    }
    if overlay_unit_title is not None:
        overlay["units"] = {
            "ru.b1.unit40.rasskaz": {"title": overlay_unit_title}
        }
    if overlay_lesson_title is not None:
        overlay["lessons"] = {
            "ru.b1.unit40.lesson02": {"title": overlay_lesson_title}
        }
    return realization, overlay


def test_content_field_length_validator_accepts_titles_at_the_column_limit():
    compiler = load_content_compiler()
    report = compiler.Report()
    limit = compiler.MAX_CONTENT_TITLE_LENGTH

    realization, overlay = length_documents(
        course_title="C" * limit,
        unit_title="U" * limit,
        lesson_title="L" * limit,
        teaching_title="T" * limit,
        teaching_key="ru." + "k" * (compiler.MAX_CONTENT_KEY_LENGTH - 3),
    )
    compiler.validate_content_field_lengths(realization, overlay, report)

    assert report.errors == []
    assert report.warnings == []


def test_content_field_length_validator_rejects_over_length_teaching_title():
    compiler = load_content_compiler()
    report = compiler.Report()

    realization, overlay = length_documents(
        teaching_title="T" * (compiler.MAX_CONTENT_TITLE_LENGTH + 1),
    )
    compiler.validate_content_field_lengths(realization, overlay, report)

    assert any(
        "overlay.teaching.ru.b1.unit40.lesson02.teach.hotja.title" in error
        and "ContentItem.title is VARCHAR(200)" in error
        for error in report.errors
    ), report.errors


def test_content_field_length_validator_rejects_over_length_course_unit_lesson_titles():
    compiler = load_content_compiler()
    report = compiler.Report()
    too_long = compiler.MAX_CONTENT_TITLE_LENGTH + 1

    realization, overlay = length_documents(
        course_title="C" * too_long,
        unit_title="U" * too_long,
        lesson_title="L" * too_long,
    )
    compiler.validate_content_field_lengths(realization, overlay, report)

    assert any(
        error.startswith("overlay.course.title") for error in report.errors
    )
    assert any(
        error.startswith("realization.units[0].title")
        for error in report.errors
    )
    assert any(
        error.startswith("realization.units[0].lessons[0].title")
        for error in report.errors
    )


def test_content_field_length_validator_checks_the_effective_overriding_title():
    compiler = load_content_compiler()
    too_long = compiler.MAX_CONTENT_TITLE_LENGTH + 1

    # A long realization title that the overlay replaces never reaches the
    # database -- reporting it would be a false positive.
    overridden = compiler.Report()
    realization, overlay = length_documents(
        unit_title="U" * too_long,
        lesson_title="L" * too_long,
        overlay_unit_title="Storytelling",
        overlay_lesson_title="Connectors",
    )
    compiler.validate_content_field_lengths(realization, overlay, overridden)
    assert overridden.errors == []

    # ...and the overlay title that DOES win is the one that gets checked.
    overriding = compiler.Report()
    realization, overlay = length_documents(
        unit_title="Storytelling",
        overlay_unit_title="U" * too_long,
    )
    compiler.validate_content_field_lengths(realization, overlay, overriding)
    assert any(
        error.startswith("overlay.units.ru.b1.unit40.rasskaz.title")
        for error in overriding.errors
    ), overriding.errors


def test_content_field_length_validator_rejects_over_length_content_keys():
    compiler = load_content_compiler()
    report = compiler.Report()
    too_long = "ru." + "k" * compiler.MAX_CONTENT_KEY_LENGTH

    realization, overlay = length_documents(
        teaching_key=too_long,
        exercise_key=too_long + ".order",
    )
    compiler.validate_content_field_lengths(realization, overlay, report)

    assert any(
        "teaching[0].content_key" in error
        and "ContentItem.content_key is VARCHAR(255)" in error
        for error in report.errors
    ), report.errors
    assert any(
        "exercises[0].content_key" in error
        and "Exercise.content_key is VARCHAR(255)" in error
        for error in report.errors
    ), report.errors


def test_content_field_length_limits_match_the_backend_columns():
    compiler = load_content_compiler()

    for class_name in ("Course", "Unit", "Lesson", "ContentItem"):
        assert (
            _backend_varchar_width(class_name, "title")
            == compiler.MAX_CONTENT_TITLE_LENGTH
        ), f"{class_name}.title width drifted from the compiler's limit"

    for class_name in ("Unit", "Lesson", "Exercise", "ContentItem"):
        assert (
            _backend_varchar_width(class_name, "content_key")
            == compiler.MAX_CONTENT_KEY_LENGTH
        ), f"{class_name}.content_key width drifted from the compiler's limit"


def test_new_backend_mirror_validators_are_registered_in_validate_documents():
    compiler = load_content_compiler()
    realization, overlay = length_documents(
        teaching_title="T" * (compiler.MAX_CONTENT_TITLE_LENGTH + 1),
    )
    realization["units"][0]["lessons"][0]["teaching"][0]["kind"] = "grammar"
    realization["units"][0]["lessons"][0]["exercises"][0]["type"] = "bogus"

    report = compiler.validate_documents({}, realization, overlay)

    assert any("not a valid teaching card kind" in e for e in report.errors)
    assert any("not a valid exercise type" in e for e in report.errors)
    assert any("VARCHAR(200)" in e for e in report.errors)


def test_matching_pairs_untaught_target_description_warns():
    compiler = load_content_compiler()
    report = compiler.Report()
    exercise = {
        "content_key": "de.a1.unit06.lesson01.exercise04.match_family_words",
        "type": "matching_pairs",
        "pairs": [{"left": "männlicher Elternteil", "right": "Vater"}],
    }

    compiler.validate_matching_pairs_untaught_descriptions(
        exercise,
        "realization.units[0].lessons[0].exercises[0]",
        "de",
        {"männlicher", "elternteil", "vater"},
        {"vater"},
        report,
    )

    assert len(report.warnings) == 1
    assert "de.a1.unit06.lesson01.exercise04.match_family_words" in report.warnings[0]
    assert "text 'männlicher Elternteil'" in report.warnings[0]
    assert "untaught tokens: elternteil, männlicher" in report.warnings[0]


def test_matching_pairs_source_numeric_and_proper_noun_texts_are_clean():
    compiler = load_content_compiler()
    report = compiler.Report()
    exercise = {
        "content_key": "de.a1.unit06.lesson01.exercise04.clean_pairs",
        "type": "matching_pairs",
        "pairs": [
            {"left": "male parent", "right": "Vater"},
            {"left": "12 Uhr morgens", "right": "Mittag"},
            {"left": "Anna Schmidt", "right": "Nachbarin"},
        ],
    }

    compiler.validate_matching_pairs_untaught_descriptions(
        exercise,
        "realization.units[0].lessons[0].exercises[0]",
        "de",
        {
            "anna",
            "morgens",
            "nachbarin",
            "schmidt",
            "mittag",
            "uhr",
            "vater",
        },
        {"mittag", "nachbarin", "vater"},
        report,
    )

    assert report.warnings == []


def test_matching_pairs_taught_vocabulary_phrase_is_clean():
    compiler = load_content_compiler()
    report = compiler.Report()
    exercise = {
        "content_key": "de.a1.unit01.lesson05.exercise04.match_greeting",
        "type": "matching_pairs",
        "pairs": [{"left": "Guten Morgen", "right": "good morning"}],
    }

    compiler.validate_matching_pairs_untaught_descriptions(
        exercise,
        "realization.units[0].lessons[0].exercises[0]",
        "de",
        {"guten", "morgen"},
        {"guten", "morgen"},
        report,
    )

    assert report.warnings == []


def matching_pairs_override_documents():
    content_key = "de.test.exercise.match_family"
    realization_pairs = [
        {"left": "Vater", "right": "father"},
        {"left": "Mutter", "right": "mother"},
    ]
    realization = {
        "target_language": "de",
        "units": [
            {
                "lessons": [
                    {
                        "teaching": [],
                        "exercises": [
                            {
                                "content_key": content_key,
                                "type": "matching_pairs",
                                "tested_text": "Vater Mutter",
                                "prompt": {"target_blocks": []},
                                "pairs": realization_pairs,
                            }
                        ],
                    }
                ]
            }
        ],
    }
    return content_key, realization_pairs, realization


def test_matching_pairs_overlay_override_compiles_effective_pairs():
    compiler = load_content_compiler()
    content_key, realization_pairs, realization = (
        matching_pairs_override_documents()
    )
    override_pairs = [
        {"left": "Vater", "right": "padre"},
        {"left": "Mutter", "right": "madre"},
    ]
    exercise_overlay = {
        "pairs": override_pairs,
        "accepted_answers": [
            {"value": override_pairs, "status": "correct"},
        ],
    }
    overlay = {"exercises": {content_key: exercise_overlay}}
    report = compiler.Report()

    compiler.validate_matching_pairs_overlay_overrides(
        realization,
        overlay,
        report,
    )
    compiler.validate_matching_pairs_overlay_mirror(
        realization,
        overlay,
        report,
    )
    compiled = compiler.compile_exercise(
        realization["units"][0]["lessons"][0]["exercises"][0],
        exercise_overlay,
        1,
        "es",
        "de",
        content_key,
    )

    assert report.errors == []
    assert compiled["prompt"]["pairs"] == override_pairs
    assert compiled["prompt"]["pairs"] is not override_pairs
    assert realization_pairs[0]["right"] == "father"


@pytest.mark.parametrize(
    "override_pairs",
    [
        [
            {"left": "Mutter", "right": "madre"},
            {"left": "Vater", "right": "padre"},
        ],
        [
            {"left": "Väter", "right": "padres"},
            {"left": "Mutter", "right": "madre"},
        ],
    ],
)
def test_matching_pairs_overlay_override_rejects_answer_side_mismatch(
    override_pairs,
):
    compiler = load_content_compiler()
    content_key, _, realization = matching_pairs_override_documents()
    report = compiler.Report()

    compiler.validate_matching_pairs_overlay_overrides(
        realization,
        {"exercises": {content_key: {"pairs": override_pairs}}},
        report,
    )

    assert any(
        "answer side (left) must be byte-identical" in error
        and "only right-side clues may differ" in error
        for error in report.errors
    ), report.errors


def test_matching_pairs_overlay_override_rejects_pair_count_mismatch():
    compiler = load_content_compiler()
    content_key, _, realization = matching_pairs_override_documents()
    report = compiler.Report()

    compiler.validate_matching_pairs_overlay_overrides(
        realization,
        {
            "exercises": {
                content_key: {
                    "pairs": [{"left": "Vater", "right": "padre"}],
                }
            }
        },
        report,
    )

    assert any(
        "override pair count must match realization pairs exactly" in error
        and "2 realization pair(s) vs 1 override pair(s)" in error
        for error in report.errors
    ), report.errors


def test_matching_pairs_without_overlay_override_keeps_realization_pairs():
    compiler = load_content_compiler()
    content_key, realization_pairs, realization = (
        matching_pairs_override_documents()
    )
    exercise_overlay = {
        "accepted_answers": [
            {"value": realization_pairs, "status": "correct"},
        ],
    }

    compiled = compiler.compile_exercise(
        realization["units"][0]["lessons"][0]["exercises"][0],
        exercise_overlay,
        1,
        "en",
        "de",
        content_key,
    )

    assert compiled == {
        "type": "matching_pairs",
        "order": 1,
        "prompt": {
            "text_blocks": [],
            "answer_language_code": "de",
            "pairs": realization_pairs,
        },
        "correct_response": realization_pairs,
        "feedback": None,
        "xp": 10,
        "content_key": content_key,
    }


def test_matching_pairs_override_answers_must_mirror_effective_pairs():
    compiler = load_content_compiler()
    content_key, realization_pairs, realization = (
        matching_pairs_override_documents()
    )
    override_pairs = [
        {"left": "Vater", "right": "padre"},
        {"left": "Mutter", "right": "madre"},
    ]
    report = compiler.Report()

    compiler.validate_matching_pairs_overlay_mirror(
        realization,
        {
            "exercises": {
                content_key: {
                    "pairs": override_pairs,
                    "accepted_answers": [
                        {"value": realization_pairs, "status": "correct"},
                    ],
                }
            }
        },
        report,
    )

    assert any(
        "answer does not mirror effective overlay pairs exactly" in error
        and "'Vater' -> 'padre'" in error
        for error in report.errors
    ), report.errors


def test_matching_pairs_untaught_validator_uses_effective_overlay_pairs():
    compiler = load_content_compiler()
    content_key, _, realization = matching_pairs_override_documents()
    lesson = realization["units"][0]["lessons"][0]
    lesson["teaching"] = [{"introduced_tokens": ["Vater", "Mutter"]}]
    target_lexicon = {"vater", "mutter", "männlicher", "elternteil"}

    target_clue_report = compiler.Report()
    compiler.validate_untaught_vocabulary(
        realization,
        target_clue_report,
        source_language="en",
        target_lexicon=target_lexicon,
        overlay={
            "exercises": {
                content_key: {
                    "pairs": [
                        {
                            "left": "Vater",
                            "right": "männlicher Elternteil",
                        },
                        {"left": "Mutter", "right": "mother"},
                    ]
                }
            }
        },
    )

    assert len(target_clue_report.warnings) == 1
    assert target_clue_report.warnings[0].startswith(
        f"overlay.exercises.{content_key}.pairs[0].right"
    )
    assert "untaught tokens: elternteil, männlicher" in (
        target_clue_report.warnings[0]
    )

    source_clue_report = compiler.Report()
    compiler.validate_untaught_vocabulary(
        realization,
        source_clue_report,
        source_language="en",
        target_lexicon=target_lexicon,
        overlay={
            "exercises": {
                content_key: {
                    "pairs": [
                        {"left": "Vater", "right": "male parent"},
                        {"left": "Mutter", "right": "mother"},
                    ]
                }
            }
        },
    )

    assert source_clue_report.warnings == []
