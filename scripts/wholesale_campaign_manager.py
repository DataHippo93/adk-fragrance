"""
ADK Fragrance Wholesale Campaign Manager

Orchestrates the Instantly.ai outreach campaigns:
  - Reads leads from data/leads.csv
  - Classifies store types
  - Creates / retrieves campaigns per store type
  - Adds new leads to appropriate campaigns
  - Checks for replies (future: forward via Graph API)
  - Sends weekly performance report via OpenClaw WhatsApp

Usage:
    python3 scripts/wholesale_campaign_manager.py [--sync-leads] [--report] [--check-replies]
"""

import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/adkadmin/adk-fragrance/scripts')
from bws_loader import load_secret
from instantly_client import (
    create_campaign,
    add_lead,
    list_campaigns,
    get_campaign_stats,
    get_campaign_leads,
    verify_token,
)
from wholesale_sequences import (
    get_sequence,
    classify_store_type,
    SEQUENCES,
)

# Paths
BASE_DIR = Path("/home/adkadmin/adk-fragrance")
LEADS_CSV = BASE_DIR / "data" / "leads.csv"
CAMPAIGN_IDS_FILE = BASE_DIR / "data" / "campaign_ids.json"

# Campaign name prefix for matching
CAMPAIGN_PREFIX = "ADK Wholesale"


def load_campaign_ids() -> dict:
    """Load saved campaign IDs from disk."""
    if CAMPAIGN_IDS_FILE.exists():
        with open(CAMPAIGN_IDS_FILE) as f:
            return json.load(f)
    return {}


def save_campaign_ids(ids: dict):
    """Save campaign IDs to disk."""
    with open(CAMPAIGN_IDS_FILE, "w") as f:
        json.dump(ids, f, indent=2)


def find_or_create_campaigns() -> dict:
    """
    Find existing ADK campaigns or create them.
    Returns dict mapping store_type -> campaign_id.
    """
    campaign_ids = load_campaign_ids()

    # Check if we already have all three
    needed_types = ["apothecary", "boutique", "outdoor"]
    missing = [t for t in needed_types if t not in campaign_ids]

    if not missing:
        print(f"All campaigns already created: {campaign_ids}")
        return campaign_ids

    # Check existing campaigns in Instantly
    existing = list_campaigns()
    existing_by_name = {c.get("name", ""): c.get("id") for c in existing}

    for store_type in missing:
        seq = get_sequence(store_type)
        campaign_name = seq["campaign_name"]

        if campaign_name in existing_by_name:
            campaign_ids[store_type] = existing_by_name[campaign_name]
            print(f"Found existing campaign for {store_type}: {campaign_ids[store_type]}")
        else:
            print(f"Creating campaign for {store_type}: {campaign_name}")
            steps = seq["steps"]
            first = steps[0]
            follow_ups = [
                {
                    "subject": s["subject"],
                    "body": s["body"],
                    "delay_days": s["delay_days"],
                    "only_if_no_reply": True,
                }
                for s in steps[1:]
            ]
            result = create_campaign(
                name=campaign_name,
                subject=first["subject"],
                body=first["body"],
                sequence_steps=follow_ups,
            )
            cid = result.get("id", "")
            campaign_ids[store_type] = cid
            print(f"  Created: {cid}")

    # coop maps to outdoor
    campaign_ids["coop"] = campaign_ids.get("outdoor", "")

    save_campaign_ids(campaign_ids)
    return campaign_ids


def load_leads() -> list:
    """Load leads from CSV."""
    leads = []
    with open(LEADS_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(row)
    return leads


def sync_leads():
    """
    Read leads.csv, classify store types, and add leads with emails
    to the appropriate Instantly campaigns.
    """
    if not verify_token():
        print("ERROR: Instantly API token is invalid. Aborting.")
        return

    campaign_ids = find_or_create_campaigns()
    leads = load_leads()

    added = 0
    skipped_no_email = 0
    errors = 0

    for lead in leads:
        email = lead.get("email", "").strip()
        if not email:
            skipped_no_email += 1
            continue

        # Classify if not set
        store_type = lead.get("store_type", "").strip()
        if not store_type:
            store_type = classify_store_type(lead.get("company", ""))

        # Map to campaign
        cid = campaign_ids.get(store_type)
        if not cid:
            cid = campaign_ids.get("boutique", "")

        first_name = lead.get("first_name", "").strip()
        last_name = lead.get("last_name", "").strip()
        company = lead.get("company", "").strip()

        # If no first name, use a generic greeting-friendly fallback
        if not first_name:
            first_name = "there"

        custom_vars = {
            "city": lead.get("city", ""),
            "state": lead.get("state", ""),
            "store_type": store_type,
            "website": lead.get("website", ""),
        }

        try:
            add_lead(
                campaign_id=cid,
                email=email,
                first_name=first_name,
                last_name=last_name,
                company=company,
                custom_vars=custom_vars,
            )
            print(f"  Added: {email} -> {store_type} campaign")
            added += 1
        except Exception as e:
            print(f"  ERROR adding {email}: {e}")
            errors += 1

    print(f"\nSync complete: {added} added, {skipped_no_email} skipped (no email), {errors} errors")


def generate_report() -> str:
    """
    Generate a performance report for all ADK campaigns.
    Returns formatted report string.
    """
    campaign_ids = load_campaign_ids()
    if not campaign_ids:
        return "No campaigns found. Run --sync-leads first."

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"ADK Wholesale Outreach Report — {now}\n"]

    for store_type in ["apothecary", "boutique", "outdoor"]:
        cid = campaign_ids.get(store_type)
        if not cid:
            continue

        seq = get_sequence(store_type)
        lines.append(f"\n{seq['campaign_name']}")
        lines.append("-" * 40)

        try:
            stats = get_campaign_stats(cid)
            sent = stats.get("sent", stats.get("total_sent", 0))
            opened = stats.get("opened", stats.get("total_opened", 0))
            replied = stats.get("replied", stats.get("total_replied", 0))
            bounced = stats.get("bounced", stats.get("total_bounced", 0))

            lines.append(f"  Sent: {sent}")
            lines.append(f"  Opened: {opened}")
            lines.append(f"  Replied: {replied}")
            lines.append(f"  Bounced: {bounced}")
            if sent > 0:
                lines.append(f"  Open rate: {opened/sent*100:.1f}%")
                lines.append(f"  Reply rate: {replied/sent*100:.1f}%")
        except Exception as e:
            lines.append(f"  Stats unavailable: {e}")

    return "\n".join(lines)


def send_report_whatsapp():
    """Send weekly performance report to Clark via OpenClaw."""
    report = generate_report()
    print(report)
    print()

    try:
        result = subprocess.run(
            ["openclaw", "message", "send", "--to", "+13152618650"],
            input=report,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print("Report sent to Clark via WhatsApp.")
        else:
            print(f"WhatsApp send failed: {result.stderr}")
    except FileNotFoundError:
        print("openclaw CLI not found — report printed above.")
    except Exception as e:
        print(f"Error sending report: {e}")


def check_replies():
    """
    Check for campaign replies and forward summaries to Elisabeth.
    Uses Microsoft Graph API via Azure credentials from Bitwarden.
    """
    campaign_ids = load_campaign_ids()
    if not campaign_ids:
        print("No campaigns found.")
        return

    # Collect reply info from all campaigns
    replies = []
    for store_type in ["apothecary", "boutique", "outdoor"]:
        cid = campaign_ids.get(store_type)
        if not cid:
            continue
        try:
            stats = get_campaign_stats(cid)
            replied_count = stats.get("replied", stats.get("total_replied", 0))
            if replied_count > 0:
                seq = get_sequence(store_type)
                replies.append({
                    "campaign": seq["campaign_name"],
                    "replied": replied_count,
                })
        except Exception as e:
            print(f"Error checking {store_type}: {e}")

    if not replies:
        print("No new replies found.")
        return

    # Build summary
    summary = "ADK Wholesale — Reply Summary\n\n"
    for r in replies:
        summary += f"- {r['campaign']}: {r['replied']} replies\n"
    summary += "\nPlease check Instantly dashboard for full reply content."

    # Send via Graph API
    try:
        tenant_id = load_secret("AZURE_TENANT_ID")
        client_id = load_secret("AZURE_CLIENT_ID")
        client_secret = load_secret("AZURE_CLIENT_SECRET")

        if not all([tenant_id, client_id, client_secret]):
            print("Azure credentials not found in Bitwarden. Printing summary instead:")
            print(summary)
            return

        import requests

        # Get access token
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        token_resp = requests.post(token_url, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        })
        access_token = token_resp.json().get("access_token")

        if not access_token:
            print("Failed to get Azure access token. Summary:")
            print(summary)
            return

        # Send email via Graph API
        send_url = "https://graph.microsoft.com/v1.0/users/wholesale@adirondackfragrance.com/sendMail"
        email_payload = {
            "message": {
                "subject": f"ADK Wholesale Replies — {datetime.now().strftime('%Y-%m-%d')}",
                "body": {"contentType": "Text", "content": summary},
                "toRecipients": [
                    {"emailAddress": {"address": "elisabeth@adkfragrancefarm.com"}}
                ],
            }
        }
        send_resp = requests.post(
            send_url,
            json=email_payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        if send_resp.ok:
            print("Reply summary forwarded to elisabeth@adkfragrancefarm.com")
        else:
            print(f"Graph API error: {send_resp.status_code} {send_resp.text[:200]}")
            print("Summary:")
            print(summary)

    except Exception as e:
        print(f"Error sending reply summary: {e}")
        print("Summary:")
        print(summary)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ADK Wholesale Campaign Manager")
    parser.add_argument("--sync-leads", action="store_true",
                        help="Sync leads from CSV to Instantly campaigns")
    parser.add_argument("--report", action="store_true",
                        help="Generate and send performance report")
    parser.add_argument("--check-replies", action="store_true",
                        help="Check for replies and forward to Elisabeth")
    parser.add_argument("--status", action="store_true",
                        help="Show campaign status summary")

    args = parser.parse_args()

    if not any([args.sync_leads, args.report, args.check_replies, args.status]):
        parser.print_help()
        return

    if args.sync_leads:
        print("=== Syncing leads to Instantly campaigns ===")
        sync_leads()

    if args.check_replies:
        print("\n=== Checking for replies ===")
        check_replies()

    if args.report:
        print("\n=== Performance Report ===")
        send_report_whatsapp()

    if args.status:
        print("\n=== Campaign Status ===")
        ids = load_campaign_ids()
        if ids:
            for k, v in ids.items():
                print(f"  {k}: {v}")
        else:
            print("  No campaigns created yet.")


if __name__ == "__main__":
    main()
