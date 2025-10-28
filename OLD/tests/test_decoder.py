# tests/test_decoder.py
from data.decoder import decode_pkm_text

def test_decode_basic_letters_and_terminator():
    # 'R' 'E' 'D' + terminator -> "RED"
    raw = [0x91, 0x84, 0x83, 0x50]
    assert decode_pkm_text(raw) == "RED"

def test_unknown_bytes_render_placeholders():
    # 0x00 is not mapped to a visible char (we expect placeholder)
    txt = decode_pkm_text([0x00], stop_at_terminator=False)
    assert "<?00>" in txt or txt == "<null>"
