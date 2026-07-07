from app.services.goldfish import _is_land


def test_is_land_detects_basic_lands():
    card = {'type_line': 'Basic Land — Forest'}
    assert _is_land(card) is True


def test_is_land_rejects_nonlands():
    card = {'type_line': 'Legendary Creature — Human Wizard'}
    assert _is_land(card) is False
