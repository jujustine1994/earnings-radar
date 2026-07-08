from unittest.mock import Mock

from earnings_radar import sec_edgar


def _fake_submissions(forms, dates, accessions):
    resp = Mock()
    resp.status_code = 200
    resp.json.return_value = {
        "filings": {
            "recent": {
                "form": forms,
                "filingDate": dates,
                "accessionNumber": accessions,
            }
        }
    }
    return resp


def test_returns_most_recent_matching_form():
    session = Mock()
    session.get.return_value = _fake_submissions(
        forms=["4", "10-Q", "8-K"],
        dates=["2026-07-01", "2026-06-30", "2026-07-30"],
        accessions=["a-1", "a-2", "a-3"],
    )

    result = sec_edgar.fetch_latest_filing("0000320193", session=session)

    assert result == {"accession_number": "a-3", "form": "8-K", "filing_date": "2026-07-30"}


def test_returns_none_when_no_matching_form():
    session = Mock()
    session.get.return_value = _fake_submissions(
        forms=["4", "3"], dates=["2026-07-01", "2026-06-30"], accessions=["a-1", "a-2"]
    )

    result = sec_edgar.fetch_latest_filing("0000320193", session=session)

    assert result is None


def test_sends_required_user_agent_header():
    session = Mock()
    session.get.return_value = _fake_submissions(forms=[], dates=[], accessions=[])

    sec_edgar.fetch_latest_filing("0000320193", session=session, contact_email="me@x.com")

    _, kwargs = session.get.call_args
    assert "me@x.com" in kwargs["headers"]["User-Agent"]
