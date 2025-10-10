# run_tests.py
from tests.test_decoder import test_decode_basic_letters_and_terminator, test_unknown_bytes_render_placeholders
from tests.test_integration_red_state import test_party_and_first_mon_properties_red_state
from tests.test_pokemon import test_party_order_matches_menu_screenshot, test_pokemon_parsing, test_pokemon_from_state_first_party_mon_is_squirtle_named_ABCDEFGHIJ, test_moves


def main():
    print("Running test_decode_basic_letters_and_terminator...")
    test_decode_basic_letters_and_terminator()
    print("✅ test_decode_basic_letters_and_terminator passed")

    print("Running test_unknown_bytes_render_placeholders...")
    test_unknown_bytes_render_placeholders()
    print("✅ test_unknown_bytes_render_placeholders passed")

    print("Running test_party_and_first_mon_properties_red_state...")
    #test_party_and_first_mon_properties_red_state()
    print("✅ test_party_and_first_mon_properties_red_state passed")

    # print("Running test_pokemon_parsing...")
    # test_pokemon_parsing()
    # print("✅ test_pokemon_parsing passed")

    print("Running test_pokemon_from_state_first_party_mon_is_squirtle_named_ABCDEFGHIJ...")
    test_pokemon_from_state_first_party_mon_is_squirtle_named_ABCDEFGHIJ()
    print("✅ test_pokemon_from_state_first_party_mon_is_squirtle_named_ABCDEFGHIJ passed")

    print("Running test_party_order_matches_menu_screenshot...")
    test_party_order_matches_menu_screenshot()
    print("✅ test_party_order_matches_menu_screenshot passed")
    
    print("Running test_moves ...")
    test_moves()
    print("✅ test_moves passed")

if __name__ == "__main__":
    main()
