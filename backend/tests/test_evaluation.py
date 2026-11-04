from navylink.evaluate import evaluate


def test_labeled_evaluation_is_repeatable_and_grounded():
    first, second = evaluate(), evaluate()
    assert first["queries"] == second["queries"]
    assert first["proposals"] == second["proposals"]
    assert first["pairs"] == second["pairs"]
    for report in [first, second]:
        summary = report["summary"]
        assert summary["queries"] >= 15
        assert summary["near_duplicate_proposals"] >= 5
        assert summary["complementary_or_nonduplicate_proposals"] >= 5
        assert summary["recall_at_5"] >= .9
        assert summary["duplicate_precision"] >= .9 and summary["duplicate_recall"] >= .9
        assert summary["workflow_success_rate"] == 1
        assert summary["citations_checked"] > 0
        assert summary["citations_valid"] == summary["citations_checked"]
        assert summary["candidates_with_complete_constraints"] == summary["candidates_checked"]
        assert summary["permission_checks_passed"] == summary["permission_checks_total"]
        assert summary["unrelated_pairs_in_top_6"] == 0
