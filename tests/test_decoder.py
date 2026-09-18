"""Tests for game.data.decoder's Gen1 text encode/decode round-trip."""
import pytest

from game.data.decoder import decode_pkm_text, encode_pkm_text


def test_encode_then_decode_round_trips():
    encoded = encode_pkm_text("PIKACHU", length=11)
    assert decode_pkm_text(encoded) == "PIKACHU"


def test_encode_pads_to_exact_length_with_terminator():
    encoded = encode_pkm_text("MEW", length=11)
    assert len(encoded) == 11
    assert encoded[3] == 0x50  # terminator right after the 3 real characters
    assert all(b == 0x50 for b in encoded[3:])


def test_encode_truncates_names_too_long_for_the_field():
    encoded = encode_pkm_text("SOMETHINGVERYLONG", length=11)
    assert len(encoded) == 11
    assert encoded[-1] == 0x50  # still terminated, even truncated


def test_encode_raises_on_unencodable_character():
    with pytest.raises(ValueError):
        encode_pkm_text("Pokemon@Home", length=11)  # '@' has no Gen1 mapping
