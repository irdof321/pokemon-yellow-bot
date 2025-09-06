# --- Base Gen I (R/B/Y) character map ---
# Common references:
#  - 0x50: end of string
#  - 0x7F: space
#  - 0x80-0x99: 'A'..'Z'
#  - 0xA0-0xB9: 'a'..'z'
#  - 0xF6-0xFF: '0'..'9'
#  - Special codes 0x49–0x5F (see control table)

PKM_GEN1_TABLE = {
    0x00: "<null>",

    # Control / variable codes
    0x49: "<page>",
    0x4A: "<pkmn>",
    0x4B: "<_cont>",
    0x4C: "<autocont>",
    0x4E: "<nextline>",
    0x4F: "<bottomline>",
    0x50: "",             # terminator (end of string)
    0x51: "<paragraph>",
    0x52: "<player>",
    0x53: "<rival>",
    0x54: "<poke>",
    0x55: "<cont>",
    0x56: "……",
    0x57: "<done>",
    0x58: "<prompt>",
    0x59: "<target>",
    0x5A: "<user>",
    0x5B: "<pc>",
    0x5C: "<tm>",
    0x5D: "<trainer>",
    0x5E: "<rocket>",
    0x5F: "<dex>",

    0x7F: " ",       # space

    # A..Z
    **{0x80 + i: chr(ord('A') + i) for i in range(26)},
    # a..z
    **{0xA0 + i: chr(ord('a') + i) for i in range(26)},

    # Digits 0..9
    **{0xF6 + i: str(i) for i in range(10)},

    # Known punctuation / symbols (extend as needed)
    0xE3: "…",      # ellipsis
    0xE6: "’",      # apostrophe
    0xE7: "♂",
    0xE8: "♀",
    0xE9: "é",
    0xE0: "Pk",     # ligature PK
    0xE1: "Mn",     # ligature MN

    # Example placeholders for additional punctuation
    # 0xEA: "(", 0xEB: ")", 0xEC: ":", 0xED: ";", 0xEE: "?", 0xEF: "!"
}


def decode_pkm_text(bytes_, table=PKM_GEN1_TABLE, stop_at_terminator=True):
    """
    Decode a list of Gen I bytes -> string.
    - stop_at_terminator: if True, stops at 0x50.
    - table: dict {byte:int -> str}; unknown bytes become "<?xx>".
    """
    out = []
    for b in bytes_:
        if stop_at_terminator and b == 0x50:
            break
        if b in table:
            out.append(table[b])
        else:
            out.append(f"<?{b:02X}>")
    return "".join(out)
