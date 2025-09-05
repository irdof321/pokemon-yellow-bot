# --- Table de base Gen I (R/B/Y) à ajuster selon ton tableau ---
# Références usuelles:
#  - 0x50: fin de chaîne
#  - 0x7F: espace
#  - 0x80-0x99: 'A'..'Z'
#  - 0xA0-0xB9: 'a'..'z'
#  - 0xF6-0xFF: '0'..'9' (ordre fréquent)
# Certains symboles/ligatures ('PK','MN','é', flèches, etc.) varient: complète-les ci-dessous.

PKM_GEN1_TABLE = {
    0x50: "",        # terminator (stop)
    0x7F: " ",       # espace

    # A..Z
    **{0x80 + i: chr(ord('A') + i) for i in range(26)},
    # a..z
    **{0xA0 + i: chr(ord('a') + i) for i in range(26)},

    # Chiffres 0..9 (mappage courant en Gen I)
    **{0xF6 + i: str(i) for i in range(10)},

    # Quelques ponctuations fréquemment vues (à ajuster)
    0xE3: "…",      # ellipsis (exemple – vérifie dans ton tableau)
    0xE6: "’",      # apostrophe typographique (exemple)
    0xE7: "♂",      # male
    0xE8: "♀",      # female
    0xE9: "é",      # é (souvent présent)
    # Ligatures / tokens spéciaux (selon tables RBY)
    0xE0: "Pk",     # à remplacer par le vrai glyphe “PK”
    0xE1: "Mn",     # à remplacer par le vrai glyphe “MN”

    # Ajoute ici tout ce que montre ton screenshot (flèches, guillemets, etc.)
    # Exemple de placeholders:
    # 0xEA: "(", 0xEB: ")", 0xEC: ":", 0xED: ";", 0xEE: "?", 0xEF: "!"
}

def decode_pkm_text(bytes_, table=PKM_GEN1_TABLE, stop_at_terminator=True):
    """
    Décode une liste d'octets Gen I -> string.
    - stop_at_terminator: si True, coupe à 0x50.
    - table: dict {octet:int -> str} ; les inconnus deviennent "<?xx>".
    """
    out = []
    for b in bytes_:
        if stop_at_terminator and b == 0x50:
            break
        if b in table:
            out.append(table[b])
        else:
            out.append(f"<?{b:02X}>")  # aide à repérer ce qu’il manque
    return "".join(out)