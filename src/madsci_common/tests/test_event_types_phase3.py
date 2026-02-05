from madsci.common.types.event_types import EVENT_TYPE_DESCRIPTIONS, EventType


def test_event_type_descriptions_cover_all_members() -> None:
    missing = [et for et in EventType if et not in EVENT_TYPE_DESCRIPTIONS]
    assert not missing, f"Missing EventType descriptions: {missing}"


def test_event_type_descriptions_not_empty() -> None:
    empty = [et for et, desc in EVENT_TYPE_DESCRIPTIONS.items() if not desc.strip()]
    assert not empty, f"Empty EventType descriptions: {empty}"
