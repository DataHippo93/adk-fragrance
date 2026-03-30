#!/usr/bin/env python3
"""
ADK Fragrance Farm — Churn Report
Runs against Method CRM (all invoice customers) + writes dated tabs to SharePoint.
Excludes: Empire State Development
Scope: ALL customers billed by invoice (wholesale, private label, retail, etc.)
Schedule: Daily on-demand or via cron. Each run creates new dated tabs.
"""

import urllib.request, urllib.parse, json, time, datetime, os
from collections import defaultdict

# ── Credentials (loaded from environment — set via /home/adkadmin/.openclaw/.env.adk) ──
TENANT_ID     = os.environ.get('AZURE_TENANT_ID',     '7df011e1-eb7e-46bc-b4f8-9ea223936cc6')
CLIENT_ID     = os.environ.get('AZURE_CLIENT_ID',     'b38234ad-7453-4a53-8353-25bf63852d2d')
CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET', '')
METHOD_KEY    = os.environ.get('METHOD_API_KEY',       '')
DRIVE_ID      = os.environ.get('ADK_DRIVE_ID',        'b!pcjjny-J-Uu4xgIyVeZVpeRPvwgb0_JNjTJSMa0ej5COqk4tEzVASpG7bHYHB4iD')
CHURN_FILE_ID = os.environ.get('ADK_CHURN_FILE_ID',   '01L4XUX47I62X427CM3FE2GLEI3BGR3EEY')
WHATSAPP_TO   = '+13152618650'

# Load from Bitwarden if env vars not set
if not CLIENT_SECRET or not METHOD_KEY:
    import sys
    sys.path.insert(0, '/home/adkadmin/.openclaw/workspace/scripts')
    try:
        from bws_loader import load_secret
        if not CLIENT_SECRET:
            CLIENT_SECRET = load_secret('AZURE_CLIENT_SECRET')
        if not METHOD_KEY:
            METHOD_KEY = load_secret('METHOD_API_KEY')
    except Exception:
        pass

if not CLIENT_SECRET or not METHOD_KEY:
    raise RuntimeError("Missing credentials — ensure BWS_ACCESS_TOKEN is set in environment")

# ── Exclusions ─────────────────────────────────────────────────────────────────
EXCLUDED_CUSTOMERS = {'empire state development'}   # lowercase match

# ── Date config ────────────────────────────────────────────────────────────────
TODAY     = datetime.date.today().strftime('%Y-%m-%d')
YTD_MD    = datetime.date.today().strftime('-%m-%d')   # e.g. -03-28
BASE_GRAPH  = 'https://graph.microsoft.com/v1.0'
BASE_METHOD = 'https://rest.method.me/api/v1'


def get_token():
    url  = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token'
    data = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default'
    }).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())['access_token']


def method_fetch_all(table, params, max_records=80000):
    headers = {'Authorization': f'APIKey {METHOD_KEY}'}
    params['top'] = '100'
    url = f'{BASE_METHOD}/tables/{table}?' + urllib.parse.urlencode(params)
    results = []
    while url and len(results) < max_records:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            print(f'Method API error {e.code}: {e.read()[:100]}')
            break
        batch = data.get('value', [])
        results.extend(batch)
        url = data.get('nextLink')
        if len(batch) < 100:
            break
        time.sleep(0.2)
    return results


def graph_patch(token, item_id, sheet_name, range_addr, values):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    enc = urllib.parse.quote(sheet_name)
    url = (f'{BASE_GRAPH}/drives/{DRIVE_ID}/items/{item_id}'
           f'/workbook/worksheets(\'{enc}\')/range(address=\'{range_addr}\')')
    data = json.dumps({'values': values}).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method='PATCH')
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def graph_create_sheet(token, item_id, name):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    url = f'{BASE_GRAPH}/drives/{DRIVE_ID}/items/{item_id}/workbook/worksheets'
    data = json.dumps({'name': name}).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as r:
            print(f'  Created sheet: {name}')
    except urllib.error.HTTPError as e:
        err = e.read()
        if b'nameAlreadyExists' in err or b'already' in err.lower():
            print(f'  Sheet exists (ok): {name}')
        else:
            raise


def graph_clear_sheet(token, item_id, sheet_name):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    enc = urllib.parse.quote(sheet_name)
    url = f'{BASE_GRAPH}/drives/{DRIVE_ID}/items/{item_id}/workbook/worksheets(\'{enc}\')/usedRange'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    try:
        with urllib.request.urlopen(req) as r:
            used = json.loads(r.read())
        addr = used.get('address', '').split('!')[-1]
        if not addr:
            return
        clear_url = (f'{BASE_GRAPH}/drives/{DRIVE_ID}/items/{item_id}'
                     f'/workbook/worksheets(\'{enc}\')/range(address=\'{addr}\')/clear')
        data = json.dumps({'applyTo': 'All'}).encode()
        req2 = urllib.request.Request(clear_url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req2) as r:
            pass
        print(f'  Cleared: {sheet_name}')
    except Exception as e:
        print(f'  Clear skipped ({e})')


def is_excluded(name):
    return name.strip().lower() in EXCLUDED_CUSTOMERS


# ── MAIN ───────────────────────────────────────────────────────────────────────
def run():
    print(f'=== ADK Churn Report — {TODAY} ===')

    # 1. Token
    token = get_token()
    print('Token acquired')

    # 2. Fetch all invoices from Method CRM
    print('Fetching all invoices from Method CRM...')
    invoices = method_fetch_all('Invoice', {
        'select': 'RecordID,TxnDate,Customer,Customer_RecordID,Amount',
    })
    print(f'Total invoices: {len(invoices)}')

    # 3. Bucket by customer + year, apply exclusions
    cust_year = defaultdict(lambda: defaultdict(float))
    cust_name = {}
    excluded_count = 0

    for inv in invoices:
        cust_id  = inv.get('Customer_RecordID') or inv.get('Customer') or ''
        name     = (inv.get('Customer') or 'Unknown').strip()
        try:
            amount = float(inv.get('Amount') or 0)
        except:
            amount = 0
        date_str = (inv.get('TxnDate') or '')[:10]
        if not date_str or not cust_id:
            continue
        if is_excluded(name):
            excluded_count += 1
            continue
        year = date_str[:4]
        if year in ('2022', '2023', '2024', '2025', '2026'):
            cust_year[cust_id][year] += amount
            cust_name[cust_id] = name

    print(f'Unique customers (after exclusions): {len(cust_year)}  |  Excluded invoices: {excluded_count}')

    # 4. Build per-customer rows
    rows = []
    for cust_id, years in cust_year.items():
        name     = cust_name.get(cust_id, 'Unknown')
        rev2022  = years.get('2022', 0)
        rev2023  = years.get('2023', 0)
        rev2024  = years.get('2024', 0)
        rev2025  = years.get('2025', 0)
        rev2026  = years.get('2026', 0)
        churned  = rev2024 > 0 and rev2025 == 0 and rev2026 == 0
        at_risk  = rev2024 > 0 and rev2025 > 0 and rev2025 < rev2024 * 0.5
        new_2025 = rev2023 == 0 and rev2024 == 0 and rev2025 > 0
        yoy_2324 = round((rev2024-rev2023)/rev2023*100,1) if rev2023 > 0 else None
        yoy_2425 = round((rev2025-rev2024)/rev2024*100,1) if rev2024 > 0 else None
        rows.append({
            'name': name, 'cust_id': cust_id,
            'rev2022': rev2022, 'rev2023': rev2023, 'rev2024': rev2024,
            'rev2025': rev2025, 'rev2026': rev2026,
            'yoy_2324': yoy_2324, 'yoy_2425': yoy_2425,
            'churned': churned, 'at_risk': at_risk, 'new_2025': new_2025,
        })

    rows.sort(key=lambda x: x['rev2024'], reverse=True)

    # 5. YTD comparison — same calendar window for 2025 vs 2026
    ytd_cutoff = YTD_MD   # e.g. -03-28
    ytd_2025 = defaultdict(float)
    ytd_2026 = defaultdict(float)
    ytd_name = {}

    for inv in invoices:
        cust_id  = inv.get('Customer_RecordID') or inv.get('Customer') or ''
        name     = (inv.get('Customer') or 'Unknown').strip()
        if is_excluded(name) or not cust_id:
            continue
        try:
            amount = float(inv.get('Amount') or 0)
        except:
            amount = 0
        date_str = (inv.get('TxnDate') or '')[:10]
        if not date_str:
            continue
        year   = date_str[:4]
        mo_day = date_str[4:]
        ytd_name[cust_id] = name
        if year == '2025' and mo_day <= ytd_cutoff:
            ytd_2025[cust_id] += amount
        elif year == '2026' and mo_day <= ytd_cutoff:
            ytd_2026[cust_id] += amount

    total_ytd_2025 = sum(ytd_2025.values())
    total_ytd_2026 = sum(ytd_2026.values())
    yoy_ytd = round((total_ytd_2026 - total_ytd_2025) / total_ytd_2025 * 100, 1) if total_ytd_2025 > 0 else 0

    # 6. Totals
    total = {y: sum(r[f'rev{y}'] for r in rows) for y in (2022,2023,2024,2025,2026)}
    active_2024  = sum(1 for r in rows if r['rev2024'] > 0)
    active_2025  = sum(1 for r in rows if r['rev2025'] > 0)
    churned_list = [r for r in rows if r['churned']]
    at_risk_list = [r for r in rows if r['at_risk']]
    new_2025_list= [r for r in rows if r['new_2025']]
    churned_rev  = sum(r['rev2024'] for r in churned_list)
    new_rev_2025 = sum(r['rev2025'] for r in new_2025_list)
    net_impact   = new_rev_2025 - churned_rev
    ret_rate     = round(active_2025/active_2024*100,1) if active_2024 > 0 else 0
    yoy_2324_tot = round((total[2024]-total[2023])/total[2023]*100,1) if total[2023] > 0 else 0
    yoy_2425_tot = round((total[2025]-total[2024])/total[2024]*100,1) if total[2024] > 0 else 0

    print(f'2024 revenue: ${total[2024]:,.0f} | 2025: ${total[2025]:,.0f} | YTD 2026: ${total[2026]:,.0f}')
    print(f'YTD {TODAY[:7]} — 2025: ${total_ytd_2025:,.0f}  2026: ${total_ytd_2026:,.0f}  ({yoy_ytd:+.1f}%)')
    print(f'Churned: {len(churned_list)} customers, ${churned_rev:,.0f}')

    # 7. Write to SharePoint — dated tabs
    SHEET_CUST = f'{TODAY} Customer Data'
    SHEET_SUM  = f'{TODAY} Churn Summary'
    SHEET_YOY  = f'{TODAY} YoY Change'

    print(f'Creating SharePoint tabs for {TODAY}...')
    graph_create_sheet(token, CHURN_FILE_ID, SHEET_CUST)
    graph_create_sheet(token, CHURN_FILE_ID, SHEET_SUM)
    graph_create_sheet(token, CHURN_FILE_ID, SHEET_YOY)

    graph_clear_sheet(token, CHURN_FILE_ID, SHEET_CUST)
    graph_clear_sheet(token, CHURN_FILE_ID, SHEET_SUM)
    graph_clear_sheet(token, CHURN_FILE_ID, SHEET_YOY)

    # -- Customer Data --
    print(f'Writing {SHEET_CUST}...')
    BATCH = 100
    hdr = [['Customer', '2022', '2023', '2024', '2025', '2026 YTD',
            'YoY 23→24 %', 'YoY 24→25 %', 'Churned?', 'At Risk?', 'New in 2025?']]
    graph_patch(token, CHURN_FILE_ID, SHEET_CUST, 'A1:K1', hdr)
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i+BATCH]
        out = [[
            r['name'],
            round(r['rev2022'],2), round(r['rev2023'],2), round(r['rev2024'],2),
            round(r['rev2025'],2), round(r['rev2026'],2),
            r['yoy_2324'] if r['yoy_2324'] is not None else '',
            r['yoy_2425'] if r['yoy_2425'] is not None else '',
            'YES' if r['churned'] else 'No',
            'YES' if r['at_risk'] else 'No',
            'YES' if r['new_2025'] else 'No',
        ] for r in chunk]
        sr = i+2; er = sr+len(out)-1
        graph_patch(token, CHURN_FILE_ID, SHEET_CUST, f'A{sr}:K{er}', out)
        time.sleep(0.15)
    print(f'  {len(rows)} rows')

    # -- Churn Summary --
    print(f'Writing {SHEET_SUM}...')
    summary = [
        ['CHURN REPORT', f'As of {TODAY}'],
        ['', ''],
        [f'━━ YTD COMPARISON (Jan 1 – {TODAY[5:]}) ━━', ''],
        [f'2025 YTD Revenue', total_ytd_2025],
        [f'2026 YTD Revenue', total_ytd_2026],
        ['YTD YoY Change', f'{yoy_ytd:+.1f}%'],
        ['', ''],
        ['━━ FULL YEAR REVENUE ━━', ''],
        ['2022', total[2022]], ['2023', total[2023]], ['2024', total[2024]],
        ['2025 (Full Year)', total[2025]],
        ['2026 (YTD)', total[2026]],
        ['YoY 2023 → 2024', f'{yoy_2324_tot:+.1f}%'],
        ['YoY 2024 → 2025', f'{yoy_2425_tot:+.1f}%'],
        ['', ''],
        ['━━ CUSTOMERS ━━', ''],
        ['Active 2024', active_2024], ['Active 2025', active_2025],
        ['Retention Rate', f'{ret_rate}%'],
        ['', ''],
        ['━━ CHURN ━━', ''],
        ['Churned (active 2024, silent 2025)', len(churned_list)],
        ['Revenue Lost to Churn (2024 basis)', churned_rev],
        ['Churn Rate by Revenue', f"{round(churned_rev/total[2024]*100,1)}%"],
        ['', ''],
        ['━━ AT RISK ━━', ''],
        ['At-Risk (2025 < 50% of 2024)', len(at_risk_list)],
        ['', ''],
        ['━━ NEW CUSTOMERS 2025 ━━', ''],
        ['Count', len(new_2025_list)],
        ['Revenue', new_rev_2025],
        ['Net Revenue Impact (New − Churned)', net_impact],
        ['', ''],
        ['━━ TOP 5 CHURNED ━━', ''],
    ]
    for r in sorted(churned_list, key=lambda x: x['rev2024'], reverse=True)[:5]:
        summary.append([r['name'], round(r['rev2024'],2)])
    summary += [['', ''], ['━━ TOP 5 AT RISK ━━', '']]
    for r in sorted(at_risk_list, key=lambda x: x['rev2024'], reverse=True)[:5]:
        summary.append([r['name'], f"${r['rev2024']:,.0f} → ${r['rev2025']:,.0f}"])

    graph_patch(token, CHURN_FILE_ID, SHEET_SUM, f'A1:B{len(summary)}', summary)
    print(f'  {len(summary)} rows')

    # -- YoY Change (top 200) --
    print(f'Writing {SHEET_YOY}...')
    hdr_yoy = [['Customer', '2024 Full Year', '2025 Full Year', 'Full-Yr Change $', 'Full-Yr Change %',
                f'2025 YTD', f'2026 YTD', 'YTD Change $', 'YTD Change %', 'Status']]
    graph_patch(token, CHURN_FILE_ID, SHEET_YOY, 'A1:J1', hdr_yoy)

    top200 = [r for r in rows if r['rev2024'] > 0][:200]
    yoy_out = []
    for r in top200:
        full_delta = r['rev2025'] - r['rev2024']
        y25_ytd = ytd_2025.get(r['cust_id'], 0)
        y26_ytd = ytd_2026.get(r['cust_id'], 0)
        ytd_d   = y26_ytd - y25_ytd
        ytd_p   = round(ytd_d/y25_ytd*100,1) if y25_ytd > 0 else ''
        if r['churned']:         status = 'CHURNED'
        elif r['at_risk']:       status = 'AT RISK'
        elif y26_ytd > y25_ytd:  status = 'GROWING YTD'
        elif y26_ytd > 0:        status = 'ACTIVE'
        elif r['rev2025'] > 0:   status = 'DECLINING'
        else:                    status = 'CHURNED'
        yoy_out.append([
            r['name'],
            round(r['rev2024'],2), round(r['rev2025'],2),
            round(full_delta,2), r['yoy_2425'] if r['yoy_2425'] is not None else '',
            round(y25_ytd,2), round(y26_ytd,2),
            round(ytd_d,2), ytd_p, status
        ])

    for i in range(0, len(yoy_out), BATCH):
        chunk = yoy_out[i:i+BATCH]
        sr = i+2; er = sr+len(chunk)-1
        graph_patch(token, CHURN_FILE_ID, SHEET_YOY, f'A{sr}:J{er}', chunk)
        time.sleep(0.15)
    print(f'  {len(yoy_out)} rows')

    print(f'\nChurn report complete. Tabs written to SharePoint Churn Report.xlsx')
    return total, total_ytd_2025, total_ytd_2026, yoy_ytd, len(churned_list), churned_rev, len(at_risk_list)


if __name__ == '__main__':
    result = run()
    total, ytd25, ytd26, yoy_ytd, n_churn, churn_rev, n_risk = result
    print(f'\nSummary: 2024=${total[2024]:,.0f} | 2025=${total[2025]:,.0f} | '
          f'YTD change {yoy_ytd:+.1f}% | Churned={n_churn} (${churn_rev:,.0f}) | At-risk={n_risk}')
