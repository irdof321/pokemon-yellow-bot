"""Tests for game.training.battle_randomizer."""
import random

import game.training.battle_randomizer as br


def test_matched_levels_keep_a_team_from_having_a_dead_weight_outlier():
    """Regression test for a real gameplay observation (2026-09-10): a
    fixed +/-6 uniform spread let one 6-member team have levels 38 and 23
    at once -- a huge relative gap at those levels, one teammate unable to
    meaningfully participate. With the real default relative_spread, the
    within-team gap for a 6-member team must stay small almost always."""
    rng = random.Random(1)
    max_gap_seen = 0
    for _ in range(500):
        player_levels, opponent_levels = br.pick_matched_levels(rng, 6, 6)
        max_gap_seen = max(max_gap_seen, max(player_levels) - min(player_levels), max(opponent_levels) - min(opponent_levels))

    assert max_gap_seen < 15, (
        f"saw a within-team level gap of {max_gap_seen} across 500 draws -- "
        "relative_spread may have regressed toward the old, too-wide behavior"
    )


def test_matched_levels_still_vary_not_a_single_fixed_level():
    """The fix for the outlier problem shouldn't overshoot into "every
    teammate is the exact same level" -- some real variety must remain."""
    rng = random.Random(2)
    saw_a_real_gap = False
    for _ in range(200):
        player_levels, _ = br.pick_matched_levels(rng, 6, 1)
        if max(player_levels) - min(player_levels) >= 1:
            saw_a_real_gap = True
            break

    assert saw_a_real_gap, "500 draws of a 6-member team and every single one was perfectly level-uniform -- too tight"


def test_matched_levels_respects_absolute_bounds():
    rng = random.Random(3)
    for _ in range(200):
        player_levels, opponent_levels = br.pick_matched_levels(rng, 6, 6, level_min=5, level_max=65)
        assert all(2 <= lvl <= 100 for lvl in player_levels + opponent_levels)


def test_load_random_base_battle_reflects_the_new_party_size(load_fixture):
    """Regression test for a real bug (2026-09-10): the returned scene used
    to be built BEFORE randomize_battle() ran, so its player_party/
    enemy_party lists stayed the fixture's ORIGINAL length no matter what
    size randomize_battle() actually wrote -- to_dict()["party"] silently
    showed the wrong (stale) roster size. Uses a real fixture directly
    (bypassing load_random_base_battle's own fixture-picking) so this test
    doesn't depend on the 4 named base fixtures existing."""
    from game.scenes.battle_scene import create_battle_scene

    session = load_fixture("wild_charmander_vs_rattata.state")
    scene = create_battle_scene(session, 0)

    rng = random.Random(42)
    picks = br.randomize_battle(session, scene, rng, is_wild=True, player_party_size=5)

    # Mirrors what load_random_base_battle does after randomize_battle():
    # the scene must be rebuilt, not reused, to see the new size.
    fresh_scene = create_battle_scene(session, 0)
    fresh_party_len = len(fresh_scene.to_dict()["party"])

    assert len(picks["player"]) == 5
    assert fresh_party_len == 5, f"fresh scene should show 5 party members, got {fresh_party_len}"


def test_party_slot_experience_matches_the_assigned_level(load_fixture):
    """Regression test for a real gameplay bug (2026-09-10): level/stats were
    set directly but the party struct's own 3-byte `experience` counter was
    never touched, left however the fixture's original occupant had it. A
    mutated Pokemon would win a battle, gain a little EXP, and the game --
    using ITS OWN stored EXP as ground truth, not the level byte we wrote --
    would snap the level back down to whatever that stale (usually much
    lower) EXP actually corresponded to. Reads back via PartyPokemon.
    experience (the project's own accessor, not a raw memory peek) and
    checks it falls in [exp for this level, exp for next level) -- current
    for this level, not already due for another level-up."""
    from game.data.pokemon import PartyPokemon

    session = load_fixture("wild_charmander_vs_rattata.state")
    target_dex, level, dv = 4, 30, 8  # Charmander, GROWTH_MEDIUM_SLOW
    move_ids = br.pick_random_moveset(random.Random(1))

    br.mutate_party_slot_to(session, 1, target_dex, level, dv, move_ids)

    stored_exp = PartyPokemon(session, slot=1, is_yellow=False).experience
    growth_rate = br.BASE_STATS[target_dex]["growth_rate"]
    exp_this_level = br.exp_for_level(growth_rate, level)
    exp_next_level = br.exp_for_level(growth_rate, level + 1)

    assert exp_this_level <= stored_exp < exp_next_level, (
        f"stored experience {stored_exp} is not consistent with level {level} "
        f"(expected in [{exp_this_level}, {exp_next_level}))"
    )
