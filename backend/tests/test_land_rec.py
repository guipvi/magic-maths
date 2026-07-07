from app.services.land_rec import _count_ramp_spells


def test_count_ramp_spells_detects_sol_ring_as_ramp():
    card = {
        'name': 'Sol Ring',
        'type_line': 'Artifact',
        'oracle_text': '{T}: Add C',
        'cmc': 1,
    }

    assert _count_ramp_spells([card]) == 1
