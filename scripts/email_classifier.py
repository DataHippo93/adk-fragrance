#!/usr/bin/env python3
"""
Shared email classification module for cmaine@ycconsulting.biz mailbox triage.

Imported by:
  - realtime_triage.py    (runs every 10 min)
  - daily_mailbox_cleanup.py  (runs daily at 7:30 AM ET)

Do not add credentials or Graph API calls here — keep it pure classification logic.

─────────────────────────────────────────────────────────────────────────────
DESIGN PRINCIPLES (based on GTD / PARA / Inbox Zero best practices, 2025)
─────────────────────────────────────────────────────────────────────────────

1. PARA alignment
   - Projects  → TODAY, Nature's Cafe Project, ADK Wholesale, Grants
   - Areas     → Nature's Ops, Finance, People
   - Resources → Reading, ADK Marketing, Nature's Marketing
   - Archive   → everything else

2. TODAY must be HIGH-SIGNAL ONLY ("3–5 true signal sources" principle)
   Three gates before an email reaches TODAY:
     Gate A: known business-critical sender (Shopify, IRS, etc.)
     Gate B: strong urgency subject keyword (action required, overdue, etc.)
     Gate C: direct human-to-human mail with explicit action request
   Marketing emails must NEVER reach TODAY — own-business marketing is
   checked first, then the full marketing filter, before any TODAY logic.

3. Two-minute-rule flag
   Emails that look like quick, single-question replies are tagged "2min"
   in the subject prefix so Clark can batch-clear them quickly.
   (Currently surfaced in TODAY; a future enhancement could use a sub-folder.)

4. Thread detection
   RE: / FW: prefixes are detected early. Replies to ADK Wholesale threads
   stay in ADK Wholesale; replies to Cafe threads stay in Cafe Project.
   This prevents important follow-ups from falling into Archive.

5. Marketing false-positive reduction
   - Own-business marketing (ADK, Nature's) checked BEFORE any other filter.
   - Two-pass marketing check: sender patterns first, then subject/preview.
   - Marketing subject keywords that overlap with legitimate urgency
     (e.g. "last chance", "expires") only trigger Archive when combined
     with at least one additional marketing signal.

6. Noise → Archive immediately, never TODAY.
"""

# ── Known retail / big-box domains → always Archive ───────────────────────────
KNOWN_RETAIL_DOMAINS = [
    # Home improvement / hardware
    "lowes.com", "homedepot.com", "acehardware.com", "truevalue.com",
    "menards.com", "build.com", "grainger.com",
    # General big-box / mass retail
    "walmart.com", "target.com", "costco.com", "samsclub.com", "bjs.com",
    # Electronics / office
    "bestbuy.com", "staples.com", "officedepot.com", "officemax.com",
    "adorama.com", "bhphotovideo.com", "newegg.com",
    # Online marketplaces
    "amazon.com", "ebay.com", "etsy.com", "overstock.com",
    # Home / furniture
    "wayfair.com", "ikea.com", "williams-sonoma.com", "potterybarn.com",
    "crateandbarrel.com", "cb2.com", "westelm.com", "bedbathandbeyond.com",
    "bathandbodyworks.com", "pier1.com",
    # Apparel / department stores
    "kohls.com", "macys.com", "nordstrom.com", "jcpenney.com", "sears.com",
    "gap.com", "oldnavy.com", "bananarepublic.com", "hm.com", "zara.com",
    "uniqlo.com", "forever21.com", "express.com",
    # Grocery / pharmacy / convenience
    "kroger.com", "safeway.com", "wholefoodsmarket.com", "traderjoes.com",
    "cvs.com", "walgreens.com", "riteaid.com", "dollar-general.com",
    "dollargeneral.com", "dollartree.com", "familydollar.com",
    # Sporting goods / outdoor
    "dickssportinggoods.com", "rei.com", "cabelas.com", "basspro.com",
    "academy.com",
    # Pet
    "petsmart.com", "petco.com", "chewy.com",
    # Auto parts
    "autozone.com", "oreillyauto.com", "advanceautoparts.com",
    # Food delivery / restaurant chains
    "doordash.com", "ubereats.com", "grubhub.com",
    # Social / ad platforms (not human senders)
    "linkedin.com", "twitter.com", "facebook.com", "instagram.com",
    "pinterest.com", "tiktok.com", "youtube.com",
    # Daily-deal / coupon sites
    "groupon.com", "livingsocial.com", "coupons.com",
]

# ── Email service provider / marketing automation domains ─────────────────────
# Presence of these in a sender address means bulk/automated mail → Archive.
# Expanded in 2025 to include more ESPs that slip through.
KNOWN_ESP_DOMAINS = [
    # Major ESPs
    "mailchimp.com", "list-manage.com",          # Mailchimp
    "constantcontact.com", "r.constantcontact.com",
    "klaviyo.com", "klaviyomail.com",
    "hubspot.com", "hs-email.net",
    "marketo.com", "mktomail.com",
    "salesforce.com", "pardot.com", "exacttarget.com",
    "sendgrid.net", "sendgrid.com",
    "brevo.com", "sendinblue.com",               # Brevo (fka Sendinblue)
    "mailjet.com",
    "aweber.com",
    "getresponse.com",
    "activecampaign.com",
    "drip.com",
    "omnisend.com",
    "campaign-monitor.com", "cmail19.com", "cmail20.com",
    "mailerlite.com",
    "sendpulse.com",
    "convertkit.com", "kit.com",
    "postmarkapp.com",                           # Transactional — usually Archive
    "mailgun.org", "mailgun.net",
    # Ecommerce notification platforms
    "shopify.com", "bigcommerce.com", "woocommerce.com",
    # Substack (newsletter platform)
    "substack.com",
]

# ── Marketing/promotional sender patterns → always Archive ────────────────────
# These are partial strings matched against the full sender address (lowercased).
# Principle: sender-domain check first (most reliable), then address patterns.
MARKETING_SENDER_PATTERNS = [
    # Subdomain patterns common in bulk mail
    "email.", "mail.", "e.mail", "em.", "news.", "promo.", "offers.",
    "send.", "bulk.", "blast.", "list.", "campaign.", "broadcast.",
    # Address local-part patterns
    "marketing@", "promo@", "deals@", "promotions@", "specials@",
    "campaign@", "blast@", "bulk@", "list@",
    "newsletter", "digest", "updates@", "weekly@", "monthly@",
    "donotreply", "do-not-reply", "noreply", "no-reply",
    # Generic/impersonal senders that are rarely human
    "hello@", "hi@", "team@", "contact@",
    # ESP name fragments in subdomain (e.g. send.klaviyo.com — already in KNOWN_ESP_DOMAINS
    # but belt-and-suspenders for unusual configurations)
    "mailchimp", "constantcontact", "klaviyo", "hubspot", "marketo",
    "salesforce", "pardot", "sendgrid", "sendpulse", "aweber",
    "getresponse", "activecampaign", "drip", "omnisend", "brevo", "mailjet",
    "shopify", "bigcommerce", "woocommerce",
    "groupon", "livingsocial", "coupons",
]

# ── Marketing subject patterns ─────────────────────────────────────────────────
# IMPORTANT: Some of these phrases overlap with legitimate urgency language.
# They are only definitive when paired with a marketing sender signal.
# Standalone ambiguous phrases are listed in AMBIGUOUS_MARKETING_SUBJECT_PATTERNS
# and require TWO signals before classifying as marketing.
MARKETING_SUBJECT_PATTERNS = [
    # Clear promotional language — single signal is enough
    "% off",
    "save ", "saves you", "deal", "coupon", "promo", "sale ", "sales ",
    "discount", "special offer", "flash sale", "clearance",
    "shop now", "shop our", "buy now", "order now",
    "free shipping", "free delivery", "ships free",
    "buy one", "bogo",
    "don't miss", "act now", "hurry", "today only", "one day only",
    "24 hours only", "48 hours only",
    "you've been selected", "you have been selected",
    "claim your", "redeem your", "exclusive access", "vip access",
    "new arrivals", "just landed", "just arrived", "back in stock",
    "restocked", "now available", "introducing our",
    "unsubscribe", "manage preferences", "email preferences",
    "view in browser", "view online", "web version",
    "sponsored", "advertisement", "partner offer",
    # NOTE: order/shipping transactionals are intentionally NOT listed here.
    # They are caught by ORDER_SIGNALS_SUBJECT → "Orders" folder (Step 6a).
    # Adding them here would incorrectly archive order confirmations from retail domains.
    "welcome to", "thanks for signing up", "thank you for signing up",
    "confirm your email", "verify your email",
    # Retail day/time expiry language
    "ends sunday", "ends monday", "ends tuesday", "ends wednesday",
    "ends thursday", "ends friday", "ends saturday",
]

# These phrases ALONE are ambiguous — a real "invoice expires" or "last chance
# to renew contract" looks identical to promo language. Classify as marketing
# only when a second marketing signal is also present.
AMBIGUOUS_MARKETING_SUBJECT_PATTERNS = [
    "offer ",           # "special offer" already caught above; bare "offer" overlaps with "job offer"
    "limited time",     # real deadlines use this too
    "last chance",      # real renewal notices use this too
    "ending soon",      # grant deadlines, contract renewals
    "ends today",       # legitimate deadline emails
    "expires", "expiring",  # insurance, license, contract renewal
    "congratulations",  # could be grant award
    "please confirm",   # could be legitimate 2FA / meeting confirm
]

# ── Preview / body signals strongly indicating bulk mail ─────────────────────
PREVIEW_MARKETING_SIGNALS = [
    "unsubscribe", "opt out", "opt-out",
    "view in browser", "view online", "view as webpage",
    "email preferences", "manage preferences",
    "you are receiving this", "you received this",
    "this email was sent to", "to stop receiving",
    "©", "\u00a9",
    "high potential seller", "dear seller", "tiktok shop",
    "seller outreach", "grow your brand", "boost your sales",
    "brand collaboration", "influencer", "partnership opportunity",
    # List-Unsubscribe header echoed in preview (common in bulk mail)
    "list-unsubscribe",
    # Common CAN-SPAM / GDPR footer language
    "all rights reserved", "privacy policy", "terms of service",
    "you're receiving this because",
    "update your preferences",
]

MARKETING_NAME_KEYWORDS = [
    "tiktok", "instagram", "facebook", "twitter", "linkedin", "snapchat",
    "pinterest", "youtube", "shopify", "amazon", "ebay", "etsy", "walmart",
    "lowe's", "lowes", "home depot", "target", "best buy", "wayfair",
    "seller", "shop seller", "high potential seller", "brand partner",
    "affiliate",
]

# ── TODAY signals — Gate A: known business-critical senders ──────────────────
# Only verified business-tool / government senders that reliably produce
# action-required emails. Kept intentionally SHORT to avoid false positives.
TODAY_GATE_A_SENDER = [
    # Order & operations platforms
    "gorgias",          # customer support tickets
    "shipstation",      # shipping exceptions
    "clover",           # POS alerts
    "homebase",         # scheduling / HR alerts
    "gusto.com",        # payroll alerts
    # Wholesale platform
    "faire.com", "faire-partner",
    # Telecom / connectivity
    "regionalaccess.net",
    # Government / regulatory
    "cantonny.gov", "nysif", "irs.gov", "sba.gov",
    "health.ny.gov", "hud.gov", "usda.gov", "eda.gov",
    # NOTE: "shopify" intentionally removed from Gate A — Shopify sends
    # both critical alerts AND heavy promotional / tip emails. Those are
    # caught by subject-based Gate B instead, after marketing filter.
]

# ── TODAY signals — Gate B: high-confidence urgency subject keywords ──────────
# REMOVED from old list: "last chance", "expires", "expiring", "ending soon"
# — these overlap heavily with marketing language.
# REMOVED: "offer" — too ambiguous.
# KEPT: words that unambiguously describe an action Clark must take.
TODAY_GATE_B_SUBJECT = [
    "action required", "response needed", "reply requested", "please respond",
    "invoice due", "overdue", "past due", "payment required",
    "urgent", "time sensitive", "deadline",
    "dispute", "chargeback", "refund request", "incident", "complaint",
    "order issue", "failed", "rejected", "declined",
    "account suspended", "account on hold", "account locked",
    "your approval", "approval needed", "needs your signature",
    "final notice", "notice of", "legal notice",
]

# ── TODAY signals — Gate C: human action words ────────────────────────────────
# These indicate a real person is asking Clark to do something.
# Used only for non-automated direct mail (Gate C check includes automation guard).
ACTION_WORDS = [
    "can you", "could you", "would you", "let me know", "following up",
    "checking in", "please review", "please approve", "do you have",
    "are you able", "when can", "what do you", "please advise",
    "your thoughts", "quick question", "quick call", "have a moment",
    "get your input", "need your", "waiting on you", "waiting for you",
    "want to discuss", "want to connect", "wanted to reach out",
]

# ── Two-minute rule: very short direct questions ──────────────────────────────
# Signals that an email is likely a quick reply (< 2 min to handle).
# Used as a secondary tag within TODAY classification.
TWO_MIN_SUBJECT_SIGNALS = [
    "quick question", "quick ask", "quick call", "quick chat",
    "yes or no", "can you confirm", "do you have a minute",
    "are you available", "can we talk", "can we meet",
    "is this still", "still on for", "ok to",
]

# ── Thread / reply detection ──────────────────────────────────────────────────
# Subjects starting with these prefixes are replies or forwards.
# Thread routing: if an email is a reply, it inherits the thread's folder
# rather than being re-classified from scratch (handled in classify()).
REPLY_PREFIXES = ("re:", "fw:", "fwd:", "re[", "re :")

# Folder-specific thread keywords: if a reply subject contains these, keep it
# in the corresponding folder even if the sender looks generic.
THREAD_FOLDER_SIGNALS = {
    "Nature's Cafe Project": [
        "cafe", "café", "19 main", "renovation", "contractor", "permit",
        "construction", "build-out", "buildout", "ny forward", "groundbreaking",
        # VAPG threads
        "vapg", "value-added producer grant", "value added producer",
        # Equipment / buzzer / building-system threads
        "cafe buzzer", "buzzer system", "cafe system", "cafe equipment",
    ],
    "ADK Wholesale": [
        "wholesale", "faire", "boutique", "apothecary", "gift shop", "stockist",
        "fragrance", "adirondack", "adk",
    ],
    "Grants": [
        "grant", "funding", "award", "rfp", "proposal", "application",
        "rural development", "ny forward", "cdbg", "sbir",
    ],
    "Taxes": [
        "wray", "wray enterprises", "tax return", "tax filing",
        "1099", "w-2", "w2", "schedule c", "estimated tax",
    ],
    "Finance": [
        "invoice", "payment", "payroll", "tax", "quickbooks", "accounting",
        "bill ", "past due", "statement",
    ],
}

# ── Café project signals ──────────────────────────────────────────────────────
# Includes USDA VAPG (Value-Added Producer Grant) applications — these are
# specifically tied to the Nature's Cafe Project and must route here BEFORE
# the Grants step (step 12) so they don't fall into the generic Grants folder.
# Also includes cafe equipment, buzzer, and building-system signals from
# contractors/vendors (e.g. access-control buzzer, HVAC, kitchen equipment).
CAFE_SIGNALS = [
    "cafe", "café", "19 main", "19 main st", "groundbreaking", "renovation",
    "contractor", "permit", "construction", "build-out", "buildout",
    "ny forward", "new york forward", "expansion", "architect",
    # USDA Value-Added Producer Grant (VAPG)
    "vapg", "value-added producer grant", "value added producer",
    # Cafe equipment / buzzer / building systems
    "cafe buzzer", "buzzer system", "cafe system", "cafe equipment",
    # Groundbreaking event invitation / new chapter announcement
    "celebrating a new chapter", "new chapter for nature", "new chapter for nature's",
]

# ── ADK Fragrance Farm marketing emails → "ADK Marketing" folder ──────────────
# Clark's own business marketing emails — tracked, NOT archived.
# Checked BEFORE is_marketing() so Klaviyo/send. subdomain patterns don't Archive them.
ADK_MARKETING_SENDER_DOMAINS = [
    "adkfragrancefarm.com",
    "adkfragrance.com",
    "adirondackfragrance.com",
    "send.adkfragrancefarm.com",   # Klaviyo sending domain
    "k.adkfragrancefarm.com",      # Klaviyo alternate subdomain
]
ADK_MARKETING_NAME_KEYWORDS = [
    "adirondack fragrance",
    "adk fragrance",
    "adk fragrance farm",
]

# ── Nature's Storehouse marketing emails → "Nature's Marketing" folder ─────────
# Tracked marketing/promo emails from Nature's Storehouse, not generic Archive.
# Checked BEFORE is_marketing() so they aren't swept into Archive.
NATURES_MARKETING_SENDER_DOMAINS = [
    "naturesstorehousevt.com",
    "naturesstorehousevt",
    "naturestorehousevt.com",
    "naturesstorehousevt.klaviyomail.com",
    "send.naturesstorehousevt.com",
    "k.naturesstorehousevt.com",   # Klaviyo alternate subdomain
]
NATURES_MARKETING_NAME_KEYWORDS = [
    "nature's storehouse",
    "natures storehouse",
    "naturesstorehousevt",
]

# ── Order confirmations, shipping updates, support tickets → "Orders" ─────────
# These are transactional reference emails — important to keep findable, not Archive.
# Checked BEFORE the marketing/retail domain filter so an Amazon order confirmation
# doesn't get swept into Archive alongside their promotional emails.
ORDER_SIGNALS_SUBJECT = [
    # Order placement
    "order confirmation", "order confirmed", "order received",
    "thank you for your order", "thanks for your order", "order receipt",
    "your order #", "order #", "order no.", "order number",
    "purchase confirmation", "purchase receipt",
    # Shipping / delivery
    "shipping confirmation", "shipment confirmation", "your shipment",
    "your order has shipped", "your order is on its way",
    "order shipped", "has been shipped",
    "tracking number", "track your order", "track your package",
    "out for delivery", "your delivery", "delivery scheduled",
    "delivered", "delivery confirmation",
    "return confirmation", "return request", "return label",
    # Support / service tickets
    "ticket #", "ticket number", "your ticket",
    "case #", "case number", "your case",
    "support request", "support ticket",
    "[ticket", "[case", "[support",
    "we received your request", "we've received your",
    "your request has been", "request received",
    "reference number:", "confirmation number:",
]

# ── Nature's Storehouse / Canton store operations signals ────────────────────
NATURES_SIGNALS_SENDER = [
    "naturesstorehousecanton", "natures-storehouse", "regionalaccess.net",
    "unfi.com", "kehe.com", "rainbowcrabtree", "cantonny.gov",
]
NATURES_SIGNALS_SUBJECT = [
    "nature's", "natures storehouse", "storehouse", "canton store",
    "inventory", "supplier", "distributor", "receiving", "shelf",
    "retail", "wholesale order", "purchase order",
]

# ── ADK Fragrance Farm / Faire wholesale signals ──────────────────────────────
ADK_SIGNALS_SENDER = [
    "adkfragrancefarm", "faire.com", "faire-partner", "faire-",
    "yen@", "yen.maine",
]
ADK_SIGNALS_SUBJECT = [
    "adirondack", "adk", "fragrance", "wholesale", "faire",
    "boutique", "apothecary", "gift shop", "stockist",
    "new subscriber", "lead", "buyer",
]

# ── Taxes / accountant signals → "Taxes" folder ──────────────────────────────
# Nathan Wray / Wray Enterprises handles Clark's tax preparation.
# Route all their emails to a dedicated Taxes folder (not Finance).
TAXES_SIGNALS_SENDER = [
    "wray", "nathanwray", "wrayenterprises", "nwray",
]
TAXES_SIGNALS_SUBJECT = [
    "wray enterprises",
]

# ── Finance signals ───────────────────────────────────────────────────────────
FINANCE_SIGNALS_SENDER = [
    "chase.com", "bankofamerica", "quickbooks", "intuit", "synderapp",
    "synder", "bill.com", "paypal", "stripe", "square", "avalara",
    "turbotax", "adp.com", "paychex", "gusto.com", "wave.com",
    "shogo", "shogomails", "shogo.io",
]
FINANCE_SIGNALS_SUBJECT = [
    "invoice", "payment", "receipt", "bank", "statement", "transaction",
    "refund", "credit", "debit", "wire", "ach", "quickbooks",
    "accounting", "balance", "payroll", "tax", "1099", "w-2",
    "expense", "reimbursement", "bill ", "past due",
]

# ── Grants / economic development signals ─────────────────────────────────────
GRANTS_SIGNALS_SENDER = [
    "eda.gov", "usda.gov", "grants.gov", "nyserda.ny.gov", "anca",
    "northcountry", "sbdc", "sba.gov", "hud.gov", "epa.gov",
    "clarkson.edu", "canton.edu", "slcida", "nyseg",
]
GRANTS_SIGNALS_SUBJECT = [
    "grant", "funding", "award", "rfp", "proposal", "application",
    "economic development", "sbir", "sttr", "loan", "forgivable",
    "rural development", "resilient food", "ny forward", "cdbg",
]

# ── Newsletters / trade reading signals ──────────────────────────────────────
# Note: KNOWN_ESP_DOMAINS covers most ESP-sent newsletters at the sender level.
# These catch newsletters that come from custom domains.
READING_SIGNALS_SENDER = [
    "mailchimp", "constantcontact", "substack", "newsletter",
    "updates@", "digest@", "weekly@", "monthly@", "news@",
]
READING_SIGNALS_SUBJECT = [
    "newsletter", "digest", "weekly update", "monthly update",
    "industry news", "market update", "trade ", "webinar",
    "recap", "roundup", "insights", "trends",
]

# ── People / personal VIP contacts ────────────────────────────────────────────
# Routed to People folder, NEVER Archive.
PEOPLE_SIGNALS_SENDER = [
    "yen.maine", "yen.cody", "louis@", "maine@",
    "sandy@", "sandy.maine",
]

# ── Noise / system-generated signals → Archive ───────────────────────────────
NOISE_SIGNALS_SENDER = [
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "bounce", "mailer-daemon", "postmaster",
    "notifications@", "alerts@",
    "support@shopify", "support@faire", "support@square",
]
NOISE_SIGNALS_SUBJECT = [
    # Tech/system noise
    "dmarc", "spf", "dkim", "exchange alert", "sync issue",
    "delivery report", "read receipt",
    # Pure promotional noise (not caught earlier)
    "unsubscribe", "% off", "sale ends", "coupon",
    "offer expires", "you've been selected", "congratulations you",
]


# ─────────────────────────────────────────────────────────────────────────────
# Core detection functions
# ─────────────────────────────────────────────────────────────────────────────

def _count_marketing_signals(addr, subject, preview="", name=""):
    """
    Count how many distinct marketing signals are present.
    Returns an integer score (0 = definitely not marketing, ≥1 = likely, ≥2 = certain).
    This enables the ambiguous-pattern logic: ambiguous subject patterns only
    count toward Archive when another signal is also present.
    """
    score = 0
    s   = addr.lower()
    sub = subject.lower() if subject else ""
    pre = preview.lower() if preview else ""
    nm  = name.lower() if name else ""

    # Sender domain checks (strongest signals — count as 2 each)
    for domain in KNOWN_RETAIL_DOMAINS:
        if domain in s:
            return 10  # fast exit — retail domains are 100% marketing
    for domain in KNOWN_ESP_DOMAINS:
        if domain in s:
            return 10  # fast exit — ESP domains are 100% bulk mail

    # Sender address pattern (strong)
    for kw in MARKETING_SENDER_PATTERNS:
        if kw in s:
            score += 2
            break  # one sender pattern is enough — don't double-count

    # Sender display name keywords (medium)
    for kw in MARKETING_NAME_KEYWORDS:
        if kw in nm:
            score += 1
            break

    # Subject — clear promotional language (strong)
    for kw in MARKETING_SUBJECT_PATTERNS:
        if kw in sub:
            score += 2
            break

    # Subject — ambiguous patterns (weak — needs corroboration)
    for kw in AMBIGUOUS_MARKETING_SUBJECT_PATTERNS:
        if kw in sub:
            score += 1
            break

    # Preview / body signals (medium)
    for kw in PREVIEW_MARKETING_SIGNALS:
        if kw in pre or kw in sub:
            score += 1
            break

    return score


def is_marketing(addr, subject, preview="", name=""):
    """
    Returns True if this looks like a marketing/promotional email.

    Uses a scored approach:
      - Score ≥ 2 → marketing
      - Score == 1 from ambiguous subject alone → NOT marketing
        (prevents "expires", "last chance" from mis-classifying real notices)
    """
    return _count_marketing_signals(addr, subject, preview, name) >= 2


def is_adk_marketing(addr, name):
    """
    Returns True if this email is from ADK Fragrance Farm's marketing infrastructure.
    Route to 'ADK Marketing', not Archive.
    """
    s  = addr.lower()
    nm = name.lower() if name else ""
    for domain in ADK_MARKETING_SENDER_DOMAINS:
        if domain in s:
            return True
    for kw in ADK_MARKETING_NAME_KEYWORDS:
        if kw in nm:
            return True
    return False


def is_natures_marketing(addr, name):
    """
    Returns True if this email is from Nature's Storehouse marketing infrastructure.
    Route to "Nature's Marketing" folder instead of Archive.
    """
    s  = addr.lower()
    nm = name.lower() if name else ""
    for domain in NATURES_MARKETING_SENDER_DOMAINS:
        if domain in s:
            return True
    for kw in NATURES_MARKETING_NAME_KEYWORDS:
        if kw in nm:
            return True
    return False


def _is_reply_or_forward(subject):
    """Returns True if the subject line starts with a reply/forward prefix."""
    if not subject:
        return False
    sl = subject.lower().strip()
    return any(sl.startswith(p) for p in REPLY_PREFIXES)


def _thread_folder(subject):
    """
    For reply/forward emails, returns the folder the thread belongs to based
    on subject keywords, or None if no strong match.
    """
    if not subject:
        return None
    sub = subject.lower()
    for folder, keywords in THREAD_FOLDER_SIGNALS.items():
        for kw in keywords:
            if kw in sub:
                return folder
    return None


def classify(addr, name, subject, received, to_clark, cc_clark, preview):
    """
    Returns the target folder name for the given email.

    Folder priority order (highest → lowest):
      1.  Archive (pre-2025)
      2.  ADK Marketing / Nature's Marketing (own-business marketing — bypass all filters)
      3.  People (VIP personal contacts)
      4.  Grants sender domain (gov/org — bypass noise filter)
      5.  Finance sender domain (banks/payroll — bypass noise filter)
      5a. Taxes (Nathan Wray / Wray Enterprises)
      6.  Nature's Cafe Project (subject/preview signal)
      6a. Orders (order confirmations, shipping, support tickets — before marketing filter)
      7.  TODAY Gate A (known business-critical sender, direct only)
      8.  Marketing / noise filter → Archive
      9.  TODAY Gate B (urgency subject keyword, direct only)
     10.  TODAY Gate C (human action words, direct non-automated only)
     11.  Thread routing (RE:/FW: with folder keywords)
     12.  Grants subject signal
     13.  Finance subject signal
     14.  ADK Wholesale
     15.  Nature's Ops
     16.  Reading (newsletters)
     17.  Archive (default)

    Key design decisions:
      - Marketing filter (step 8) sits BETWEEN Gate A and Gates B/C so that
        only explicitly curated senders can reach TODAY via Gate A even if
        they also have marketing characteristics (e.g. Shopify notifications).
      - Own-business marketing (ADK, Nature's) is checked BEFORE People so
        that addresses like yenmaine@adkfragrancefarm.com don't hit People.
      - Ambiguous urgency words (expires, last chance) do NOT trigger Gate B
        alone; they require a marketing signal score < 2 AND are only in
        Gate B if they appear with a sender already past the marketing filter.
    """
    s   = addr.lower()
    sub = subject.lower() if subject else ""
    pre = preview.lower() if preview else ""

    # ── Step 1: Age gate ───────────────────────────────────────────────────────
    if received < "2025-01-01":
        return "Archive"

    # ── Step 2: Own-business marketing (bypass everything) ────────────────────
    if is_adk_marketing(addr, name):
        return "ADK Marketing"
    if is_natures_marketing(addr, name):
        return "Nature's Marketing"

    # ── Step 3: VIP personal contacts ─────────────────────────────────────────
    for kw in PEOPLE_SIGNALS_SENDER:
        if kw in s:
            return "People"

    # ── Step 4: Grants sender domains (gov/org agencies use noreply@ — bypass) ─
    for kw in GRANTS_SIGNALS_SENDER:
        if kw in s:
            return "Grants"

    # ── Step 5: Finance sender domains (banks/payroll use noreply@ — bypass) ──
    for kw in FINANCE_SIGNALS_SENDER:
        if kw in s:
            return "Finance"

    # ── Step 5a: Taxes — Nathan Wray / Wray Enterprises ───────────────────────
    for kw in TAXES_SIGNALS_SENDER:
        if kw in s:
            return "Taxes"
    for kw in TAXES_SIGNALS_SUBJECT:
        if kw in sub:
            return "Taxes"

    # ── Step 6: Café project — high-priority active project ───────────────────
    for kw in CAFE_SIGNALS:
        if kw in sub or kw in pre:
            return "Nature's Cafe Project"

    # ── Step 6a: Order confirmations / shipping updates / support tickets ────────
    # Checked BEFORE the marketing filter so transactional emails from retail
    # domains (Amazon, Best Buy, etc.) go to Orders instead of Archive.
    for kw in ORDER_SIGNALS_SUBJECT:
        if kw in sub or kw in pre:
            return "Orders"

    # ── Step 7: TODAY Gate A — known business-critical senders ────────────────
    # Only fires when email is DIRECTLY addressed to Clark (not CC).
    # These senders are explicitly vetted and should reach TODAY even if
    # their emails look automated.
    if to_clark:
        for kw in TODAY_GATE_A_SENDER:
            if kw in s:
                return "TODAY"

    # ── Step 8: Marketing / noise filter ──────────────────────────────────────
    # This is the main firewall. Runs AFTER Gate A so vetted senders get through,
    # but BEFORE Gates B/C so marketing emails can never reach TODAY via
    # subject/action-word matching.
    if is_marketing(addr, subject, preview, name):
        return "Archive"

    # Noise / auto-generated senders → Archive
    for kw in NOISE_SIGNALS_SENDER:
        if kw in s:
            return "Archive"
    for kw in NOISE_SIGNALS_SUBJECT:
        if kw in sub:
            return "Archive"

    # ── Step 9: TODAY Gate B — urgency subject keywords ───────────────────────
    # Only for emails directly to Clark, after passing marketing filter.
    if to_clark:
        for kw in TODAY_GATE_B_SUBJECT:
            if kw in sub:
                return "TODAY"

    # ── Step 10: TODAY Gate C — human action words ────────────────────────────
    # Only for non-automated direct mail to Clark.
    if to_clark:
        is_automated = any(
            kw in s for kw in ["noreply", "no-reply", "notification", "alert", "mailer"]
        )
        if not is_automated and "@" in addr:
            if any(w in sub for w in ACTION_WORDS):
                return "TODAY"
            # Question mark + personal pronoun = likely asking Clark something
            if "?" in (subject or "") and any(w in sub for w in ["you", "your", "we", "our", "i "]):
                return "TODAY"

    # ── Step 11: Thread routing ────────────────────────────────────────────────
    # RE: / FW: emails inherit the folder of their thread based on subject keywords.
    # This keeps follow-up conversations in context rather than falling to Archive.
    if _is_reply_or_forward(subject):
        thread_dest = _thread_folder(subject)
        if thread_dest:
            return thread_dest

    # ── Step 12: Grants subject signals ───────────────────────────────────────
    for kw in GRANTS_SIGNALS_SUBJECT:
        if kw in sub:
            return "Grants"

    # ── Step 13: Finance subject signals ──────────────────────────────────────
    for kw in FINANCE_SIGNALS_SUBJECT:
        if kw in sub:
            return "Finance"

    # ── Step 14: ADK Wholesale ────────────────────────────────────────────────
    for kw in ADK_SIGNALS_SENDER:
        if kw in s:
            return "ADK Wholesale"
    for kw in ADK_SIGNALS_SUBJECT:
        if kw in sub:
            return "ADK Wholesale"

    # ── Step 15: Nature's Ops ─────────────────────────────────────────────────
    for kw in NATURES_SIGNALS_SENDER:
        if kw in s:
            return "Nature's Ops"
    for kw in NATURES_SIGNALS_SUBJECT:
        if kw in sub:
            return "Nature's Ops"

    # ── Step 16: Reading (newsletters, trade pubs) ────────────────────────────
    for kw in READING_SIGNALS_SENDER:
        if kw in s:
            return "Reading"
    for kw in READING_SIGNALS_SUBJECT:
        if kw in sub:
            return "Reading"

    # ── Step 17: Default → Archive ────────────────────────────────────────────
    return "Archive"


def is_two_minute_email(subject):
    """
    Returns True if the email subject suggests a quick, ≤2-minute reply.
    Used by triage scripts to optionally tag emails for rapid batch-clearing.
    Based on GTD two-minute rule: if it takes less than 2 minutes, do it now.
    """
    if not subject:
        return False
    sub = subject.lower()
    return any(kw in sub for kw in TWO_MIN_SUBJECT_SIGNALS)
