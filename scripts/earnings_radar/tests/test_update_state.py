import argparse

from earnings_radar import update_state


def _args(**kwargs):
    defaults = {
        "command": None,
        "state": None,
        "ticker": None,
        "earnings_date": None,
        "summary": None,
        "accession": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_mark_preview_sent(tmp_path):
    state_path = str(tmp_path / "state.json")
    args = _args(
        command="mark-preview-sent",
        state=state_path,
        ticker="AAPL",
        earnings_date="2026-07-29",
        summary="Expect EPS ~$1.50",
    )

    result = update_state.apply_command(args)

    cycle = result["AAPL"]["earnings_cycles"]["2026-07-29"]
    assert cycle["preview_sent"] is True
    assert cycle["preview_summary"] == "Expect EPS ~$1.50"


def test_mark_filing_compared(tmp_path):
    state_path = str(tmp_path / "state.json")
    update_state.apply_command(
        _args(
            command="mark-preview-sent",
            state=state_path,
            ticker="AAPL",
            earnings_date="2026-07-29",
            summary="Expect EPS ~$1.50",
        )
    )

    result = update_state.apply_command(
        _args(
            command="mark-filing-compared",
            state=state_path,
            ticker="AAPL",
            earnings_date="2026-07-29",
            accession="new-2",
        )
    )

    cycle = result["AAPL"]["earnings_cycles"]["2026-07-29"]
    assert cycle["filing_compared"] is True
    assert result["AAPL"]["last_filing_accession"] == "new-2"


def test_state_persists_to_disk(tmp_path):
    state_path = str(tmp_path / "state.json")
    update_state.apply_command(
        _args(
            command="mark-preview-sent",
            state=state_path,
            ticker="AAPL",
            earnings_date="2026-07-29",
            summary="s",
        )
    )

    from earnings_radar import state as state_mod

    reloaded = state_mod.load(state_path)
    assert reloaded["AAPL"]["earnings_cycles"]["2026-07-29"]["preview_sent"] is True
