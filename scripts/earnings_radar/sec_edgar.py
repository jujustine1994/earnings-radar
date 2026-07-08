import requests

_URL_TEMPLATE = "https://data.sec.gov/submissions/CIK{cik}.json"


def fetch_latest_filing(
    cik: str,
    session=None,
    contact_email: str = "you@example.com",
    forms=("10-Q", "10-K", "8-K"),
) -> dict | None:
    http = session or requests
    headers = {"User-Agent": f"earnings-radar {contact_email}"}
    response = http.get(_URL_TEMPLATE.format(cik=cik), headers=headers)
    response.raise_for_status()

    recent = response.json().get("filings", {}).get("recent", {})
    candidates = [
        {
            "accession_number": recent["accessionNumber"][i],
            "form": recent["form"][i],
            "filing_date": recent["filingDate"][i],
        }
        for i in range(len(recent.get("form", [])))
        if recent["form"][i] in forms
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda c: c["filing_date"])
