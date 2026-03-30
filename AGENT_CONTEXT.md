# ADK Fragrance

## Purpose
Customer churn analysis, lead generation, and CRM integration for ADK Fragrance. Manages the Method CRM connection, SharePoint wholesale call list, and email-based customer classification.

## Scripts Owned
- `scripts/churn_report.py` — Customer churn analysis and reporting
- `scripts/email_classifier.py` — Email classification (copy; original in workspace/scripts/)

## Data Read/Written
- **Method CRM:** Read-only by default. Write access requires safeword: `pineapple`
- **SharePoint:** Wholesale call list (ADK drive)
- **Supabase:** adk_* tables (future)
- **Bitwarden secrets:** Method API key, ADK SharePoint drive ID (via bws_loader.py)

## Contact Routing
- Churn reports delivered to Clark (+13152618650) via WhatsApp
- Lead generation summaries delivered weekly

## Cron Jobs
- Churn report: TBD (currently manual)

## KPIs
- Churn report delivery (on schedule)
- Leads delivered per week
- SharePoint sync status

## Related Repos
- GitHub: TBD (Clark creating repo)

## Supabase Tables
- adk_* (future — to be created)
