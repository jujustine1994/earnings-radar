import json
from earnings_radar import state


def test_load_missing_file_returns_empty_dict(tmp_path):
    missing = tmp_path / "state.json"
    assert state.load(str(missing)) == {}


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    data = {"AAPL": {"last_filing_accession": "0001", "earnings_cycles": {}}}

    state.save(str(path), data)

    assert state.load(str(path)) == data


def test_set_preview_sent_creates_cycle():
    s = {}
    s = state.set_preview_sent(s, "AAPL", "2026-07-30", "Expect EPS ~$1.50")

    cycle = state.get_cycle(s, "AAPL", "2026-07-30")
    assert cycle == {
        "preview_sent": True,
        "preview_summary": "Expect EPS ~$1.50",
        "filing_compared": False,
    }


def test_get_cycle_missing_returns_empty_dict():
    assert state.get_cycle({}, "AAPL", "2026-07-30") == {}


def test_last_filing_accession_roundtrip():
    s = {}
    s = state.set_last_filing_accession(s, "AAPL", "0000320193-26-000012")

    assert state.get_last_filing_accession(s, "AAPL") == "0000320193-26-000012"


def test_get_last_filing_accession_missing_returns_none():
    assert state.get_last_filing_accession({}, "AAPL") is None


def test_set_filing_compared_updates_existing_cycle():
    s = state.set_preview_sent({}, "AAPL", "2026-07-30", "summary")
    s = state.set_filing_compared(s, "AAPL", "2026-07-30")

    cycle = state.get_cycle(s, "AAPL", "2026-07-30")
    assert cycle["filing_compared"] is True
    assert cycle["preview_summary"] == "summary"
