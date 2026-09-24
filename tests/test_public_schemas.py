"""Public schema module must remain a stable consumer boundary."""

from oskill.schemas import Scene, Script, SubjectRef


def test_public_schemas_export_video_generation_contracts() -> None:
    script = Script(
        title="test",
        description="",
        scenes=[Scene(index=0, narration="hello", duration_s=1.0, visual_description="scene")],
        estimated_duration_s=1.0,
    )
    subject = SubjectRef(subject_id="subject-1", name="Hero")

    assert script.scenes[0].narration == "hello"
    assert subject.name == "Hero"
