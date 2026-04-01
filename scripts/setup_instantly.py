#!/usr/bin/env python3
"""
One-time setup for ADK Fragrance wholesale Instantly campaigns.

  - Verifies the API token
  - Creates 3 campaign templates (apothecary, boutique, outdoor)
  - Prints campaign IDs for reference
  - Reports sending account status

Usage:
    python3 scripts/setup_instantly.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, '/home/adkadmin/adk-fragrance/scripts')

from instantly_client import verify_token, list_campaigns, create_campaign
from wholesale_sequences import (
    APOTHECARY_SEQUENCE,
    BOUTIQUE_SEQUENCE,
    OUTDOOR_SEQUENCE,
)

CAMPAIGN_IDS_FILE = Path("/home/adkadmin/adk-fragrance/data/campaign_ids.json")


def main():
    print("=" * 60)
    print("  ADK Fragrance — Instantly Campaign Setup")
    print("=" * 60)

    # Step 1: Verify token
    print("\n[1/4] Verifying Instantly API token...")
    if verify_token():
        print("  OK — Token is valid.")
    else:
        print("  FAILED — Token is invalid or API is unreachable.")
        print("  Check that INSTANTLY_API_TOKEN is set correctly in Bitwarden.")
        sys.exit(1)

    # Step 2: Check existing campaigns
    print("\n[2/4] Checking existing campaigns...")
    existing = list_campaigns()
    existing_by_name = {}
    for c in existing:
        name = c.get("name", "")
        cid = c.get("id", "")
        existing_by_name[name] = cid
        print(f"  Found: {name} ({cid})")

    if not existing:
        print("  No existing campaigns found.")

    # Step 3: Create campaigns
    print("\n[3/4] Creating campaign templates...")
    campaign_ids = {}

    for store_type, seq in [
        ("apothecary", APOTHECARY_SEQUENCE),
        ("boutique", BOUTIQUE_SEQUENCE),
        ("outdoor", OUTDOOR_SEQUENCE),
    ]:
        campaign_name = seq["campaign_name"]

        if campaign_name in existing_by_name:
            cid = existing_by_name[campaign_name]
            print(f"  {store_type}: already exists ({cid})")
            campaign_ids[store_type] = cid
        else:
            print(f"  {store_type}: creating '{campaign_name}'...")
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
            try:
                result = create_campaign(
                    name=campaign_name,
                    subject=first["subject"],
                    body=first["body"],
                    sequence_steps=follow_ups,
                )
                cid = result.get("id", "unknown")
                campaign_ids[store_type] = cid
                print(f"    Created: {cid}")
            except Exception as e:
                print(f"    ERROR: {e}")
                campaign_ids[store_type] = ""

    # coop reuses outdoor
    campaign_ids["coop"] = campaign_ids.get("outdoor", "")

    # Save IDs
    CAMPAIGN_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CAMPAIGN_IDS_FILE, "w") as f:
        json.dump(campaign_ids, f, indent=2)
    print(f"\n  Campaign IDs saved to {CAMPAIGN_IDS_FILE}")

    # Step 4: Summary
    print("\n[4/4] Setup Summary")
    print("-" * 40)
    for stype, cid in campaign_ids.items():
        status = cid if cid else "FAILED"
        print(f"  {stype:15s} -> {status}")

    print(f"\nSending account: wholesale@adirondackfragrance.com")
    print(f"Reply handler:   elisabeth@adkfragrancefarm.com")
    print()

    # Check domain warmup status
    print("Note: Domain warmup must be configured in the Instantly dashboard.")
    print("  Go to: https://app.instantly.ai/app/accounts")
    print("  Ensure wholesale@adirondackfragrance.com is connected and warming.")

    print("\n" + "=" * 60)
    print("  Setup complete. Next steps:")
    print("  1. Verify sending account in Instantly dashboard")
    print("  2. Enable domain warmup if not already active")
    print("  3. Run: python3 scripts/wholesale_campaign_manager.py --sync-leads")
    print("=" * 60)


if __name__ == "__main__":
    main()
