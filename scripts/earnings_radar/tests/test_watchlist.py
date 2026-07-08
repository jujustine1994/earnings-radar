import json
import pytest
from earnings_radar import watchlist


def test_load_returns_list_of_entries(tmp_path):
    data = [
        {"ticker": "AAPL", "cik": "0000320193", "company_name": "Apple Inc."}
    ]
    path = tmp_path / "watchlist.json"
    path.write_text(json.dumps(data))

    result = watchlist.load(str(path))

    assert result == data


def test_load_missing_file_raises(tmp_path):
    missing = tmp_path / "does_not_exist.json"

    with pytest.raises(FileNotFoundError):
        watchlist.load(str(missing))
