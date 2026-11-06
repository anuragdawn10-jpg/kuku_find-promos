from evaluator import validate_promo

def test_flags_out_of_range_duration():
    promo = {"duration_seconds": 61, "segments": [{}], "hook": "h",
             "cliffhanger": "c", "evaluation_method": "llm:test"}
    assert any("Duration" in x for x in validate_promo(promo))

def test_flags_heuristic_for_human_review():
    promo = {"duration_seconds": 30, "segments": [{}], "hook": "h",
             "cliffhanger": "c", "evaluation_method": "heuristic"}
    assert any("human/editor" in x for x in validate_promo(promo))
