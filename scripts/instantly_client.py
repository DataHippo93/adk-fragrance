"""
Instantly.ai API v2 client wrapper for ADK Fragrance wholesale outreach.
"""
import sys
import requests
from typing import Optional

sys.path.insert(0, '/home/adkadmin/adk-fragrance/scripts')
from bws_loader import load_secret

BASE_URL = "https://api.instantly.ai/api/v2"


def _get_token() -> str:
    """Load Instantly API token from Bitwarden."""
    token = load_secret("INSTANTLY_API_TOKEN")
    if not token:
        raise RuntimeError("INSTANTLY_API_TOKEN not found in Bitwarden secrets")
    return token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
    }


def _handle_response(resp: requests.Response, context: str = "") -> dict:
    """Raise on HTTP errors with useful context, return parsed JSON."""
    if not resp.ok:
        detail = resp.text[:500]
        raise RuntimeError(
            f"Instantly API error ({context}): {resp.status_code} - {detail}"
        )
    # Some endpoints return empty body on success
    if not resp.text.strip():
        return {}
    return resp.json()


def create_campaign(
    name: str,
    subject: str,
    body: str,
    sequence_steps: Optional[list] = None,
) -> dict:
    """
    Create an email campaign in Instantly.

    Args:
        name: Campaign name (internal label)
        subject: Subject line for the first email
        body: HTML or plain text body for the first email
        sequence_steps: Optional list of follow-up step dicts, each with:
            - subject (str)
            - body (str)
            - delay_days (int) - days to wait after previous step
            - only_if_no_reply (bool)

    Returns:
        Campaign object from API (includes 'id')
    """
    # Build the sequences payload — delay is in days, delay_unit = "days"
    sequences = [
        {
            "steps": [
                {
                    "type": "email",
                    "delay": 0,
                    "delay_unit": "days",
                    "variants": [
                        {"subject": subject, "body": body}
                    ],
                }
            ]
        }
    ]

    if sequence_steps:
        for step in sequence_steps:
            sequences[0]["steps"].append(
                {
                    "type": "email",
                    "delay": step.get("delay_days", 3),
                    "delay_unit": "days",
                    "variants": [
                        {
                            "subject": step.get("subject", subject),
                            "body": step["body"],
                        }
                    ],
                }
            )

    # Default schedule: weekdays 8am-5pm Eastern
    campaign_schedule = {
        "schedules": [
            {
                "name": "Weekdays",
                "timing": {"from": "08:00", "to": "17:00"},
                "days": {
                    "0": False,  # Sunday
                    "1": True,
                    "2": True,
                    "3": True,
                    "4": True,
                    "5": True,
                    "6": False,  # Saturday
                },
                "timezone": "Etc/GMT+12",
            }
        ]
    }

    payload = {
        "name": name,
        "sequences": sequences,
        "campaign_schedule": campaign_schedule,
        "stop_on_reply": True,
        "daily_limit": 20,
        "email_tag_list": [],
    }

    resp = requests.post(
        f"{BASE_URL}/campaigns",
        json=payload,
        headers=_headers(),
    )
    return _handle_response(resp, "create_campaign")


def add_lead(
    campaign_id: str,
    email: str,
    first_name: str = "",
    last_name: str = "",
    company: str = "",
    custom_vars: Optional[dict] = None,
) -> dict:
    """
    Add a single lead to a campaign.

    Args:
        campaign_id: The Instantly campaign ID
        email: Lead's email address
        first_name: Lead's first name
        last_name: Lead's last name
        company: Lead's company name
        custom_vars: Dict of custom merge variables (e.g. city, store_type)

    Returns:
        API response dict
    """
    lead = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "company_name": company,
    }
    if custom_vars:
        lead["custom_variables"] = custom_vars

    payload = {
        "campaign_id": campaign_id,
        "leads": [lead],
    }

    resp = requests.post(
        f"{BASE_URL}/leads",
        json=payload,
        headers=_headers(),
    )
    return _handle_response(resp, "add_lead")


def add_leads_bulk(campaign_id: str, leads: list) -> dict:
    """
    Add multiple leads to a campaign at once.

    Args:
        campaign_id: The Instantly campaign ID
        leads: List of dicts, each with: email, first_name, last_name,
               company, and optionally custom_vars

    Returns:
        API response dict
    """
    formatted = []
    for lead in leads:
        entry = {
            "email": lead["email"],
            "first_name": lead.get("first_name", ""),
            "last_name": lead.get("last_name", ""),
            "company_name": lead.get("company", ""),
        }
        if lead.get("custom_vars"):
            entry["custom_variables"] = lead["custom_vars"]
        formatted.append(entry)

    payload = {
        "campaign_id": campaign_id,
        "leads": formatted,
    }

    resp = requests.post(
        f"{BASE_URL}/leads",
        json=payload,
        headers=_headers(),
    )
    return _handle_response(resp, "add_leads_bulk")


def get_campaign_stats(campaign_id: str) -> dict:
    """
    Get analytics for a campaign.

    Returns:
        Dict with campaign stats (sent, opened, replied, bounced, etc.)
    """
    resp = requests.get(
        f"{BASE_URL}/campaigns/{campaign_id}/analytics",
        headers=_headers(),
    )
    return _handle_response(resp, "get_campaign_stats")


def list_campaigns(limit: int = 100) -> list:
    """List all campaigns. Returns list of campaign objects."""
    resp = requests.get(
        f"{BASE_URL}/campaigns",
        params={"limit": limit},
        headers=_headers(),
    )
    data = _handle_response(resp, "list_campaigns")
    return data if isinstance(data, list) else data.get("items", data.get("data", []))


def get_campaign(campaign_id: str) -> dict:
    """Get details for a single campaign."""
    resp = requests.get(
        f"{BASE_URL}/campaigns/{campaign_id}",
        headers=_headers(),
    )
    return _handle_response(resp, "get_campaign")


def pause_campaign(campaign_id: str) -> dict:
    """Pause an active campaign."""
    resp = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/pause",
        headers=_headers(),
    )
    return _handle_response(resp, "pause_campaign")


def resume_campaign(campaign_id: str) -> dict:
    """Resume a paused campaign."""
    resp = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/resume",
        headers=_headers(),
    )
    return _handle_response(resp, "resume_campaign")


def get_campaign_leads(campaign_id: str, limit: int = 100) -> list:
    """Get leads in a campaign."""
    resp = requests.get(
        f"{BASE_URL}/leads",
        params={"campaign_id": campaign_id, "limit": limit},
        headers=_headers(),
    )
    data = _handle_response(resp, "get_campaign_leads")
    return data if isinstance(data, list) else data.get("items", data.get("data", []))


def verify_token() -> bool:
    """Verify the API token works by listing campaigns."""
    try:
        resp = requests.get(
            f"{BASE_URL}/campaigns",
            params={"limit": 1},
            headers=_headers(),
        )
        return resp.ok
    except Exception:
        return False


if __name__ == "__main__":
    print("Verifying Instantly API token...")
    if verify_token():
        print("Token is valid.")
        campaigns = list_campaigns()
        print(f"Found {len(campaigns)} existing campaigns.")
        for c in campaigns:
            cid = c.get("id", "?")
            cname = c.get("name", "?")
            print(f"  - {cname} ({cid})")
    else:
        print("Token verification FAILED. Check INSTANTLY_API_TOKEN in Bitwarden.")
