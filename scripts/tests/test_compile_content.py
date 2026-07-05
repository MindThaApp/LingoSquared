import importlib.util
from pathlib import Path

import pytest


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
