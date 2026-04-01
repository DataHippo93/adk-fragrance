"""
Email sequences for ADK Fragrance wholesale outreach.

Three variants by store type:
  - apothecary: perfume, botanical oils, reed diffusers, natural soaps
  - boutique: Teapot Candle gift sets, soy flower candles, seasonal items
  - outdoor: Bug Armor natural repellent, Hunter's Bro cologne, outdoor candles

Each has 3 touches with merge variables: {{first_name}}, {{company}}, {{city}}

Sender: Clark Maine <wholesale@adirondackfragrance.com>
Reply handler: elisabeth@adkfragrancefarm.com
"""

FAIRE_LINK = "https://faire.com/direct/adkfragrancefarm?utm_source=widgetv1&widgetToken=bw_65jdgxvww7"
CATALOG_PDF = "https://cdn.shopify.com/s/files/1/0913/0829/4461/files/adk-wholesale-catalog_compressed_1.pdf"

# ─────────────────────────────────────────────────────
# APOTHECARY / BOTANICAL sequences
# ─────────────────────────────────────────────────────

APOTHECARY_SEQUENCE = {
    "campaign_name": "ADK Wholesale — Apothecary & Botanical Shops",
    "steps": [
        {
            "subject": "Handmade Adirondack botanicals for {{company}}",
            "body": """Hi {{first_name}},

I'm Clark Maine — my family has been crafting botanical fragrances and body care on our Adirondack farm since 1979. We're a certified MWBE, and everything we make is handcrafted in small batches using plants we grow and wildcraft ourselves.

I think our perfume oils, reed diffusers, and natural soaps would be a great fit for what you're doing at {{company}}.

Would you be open to taking a look? You can browse our wholesale line on Faire:
""" + FAIRE_LINK + """

Or just reply and I'll send over our order form directly.

Best,
Clark Maine
Adirondack Fragrance & Flavor Farm
wholesale@adirondackfragrance.com""",
            "delay_days": 0,
        },
        {
            "subject": "Re: Handmade Adirondack botanicals for {{company}}",
            "body": """Hi {{first_name}},

Wanted to follow up quickly. Our Adirondack Perfume Oil collection has been our fastest-moving wholesale item this year — shops like yours love that it's all-natural and made from botanicals we actually grow on the farm.

We offer keystone pricing across the full line, and there's no large minimum to get started.

Here's our full wholesale catalog if you'd like to take a look:
""" + CATALOG_PDF + """

Happy to answer any questions.

Clark""",
            "delay_days": 5,
        },
        {
            "subject": "Quick follow-up from ADK Fragrance",
            "body": """Hi {{first_name}},

I know inboxes get busy so I'll keep this short. If you're curious about our botanical body care but want to see the products in person first, I'm happy to send you a sample box — no strings attached.

Just reply with your shipping address and I'll get one out this week.

All the best,
Clark""",
            "delay_days": 12,
        },
    ],
}

# ─────────────────────────────────────────────────────
# BOUTIQUE / GIFT sequences
# ─────────────────────────────────────────────────────

BOUTIQUE_SEQUENCE = {
    "campaign_name": "ADK Wholesale — Boutique & Gift Shops",
    "steps": [
        {
            "subject": "Adirondack-made candles and gifts for {{company}}",
            "body": """Hi {{first_name}},

I'm Clark Maine, and my family runs Adirondack Fragrance & Flavor Farm — we've been handcrafting candles, soaps, and gift sets in the Adirondack Mountains since 1979.

Our Teapot Candle gift sets and soy flower candles have been really popular with boutiques and gift shops, and I thought they might be a nice fit for {{company}}.

If you're open to it, here's a quick look at our wholesale line on Faire:
""" + FAIRE_LINK + """

Or just reply and I'll send over the order form.

Warm regards,
Clark Maine
Adirondack Fragrance & Flavor Farm
wholesale@adirondackfragrance.com""",
            "delay_days": 0,
        },
        {
            "subject": "Re: Adirondack-made candles and gifts for {{company}}",
            "body": """Hi {{first_name}},

Just circling back. Our Teapot Candle sets have been a consistent bestseller at retail — customers love the packaging and the story behind them. They're handpoured on our farm and retail around $32, with keystone wholesale pricing.

We also have a seasonal line that does really well as impulse buys near the register.

Here's the full catalog:
""" + CATALOG_PDF + """

Let me know if you'd like to chat.

Clark""",
            "delay_days": 5,
        },
        {
            "subject": "Quick follow-up from ADK Fragrance",
            "body": """Hi {{first_name}},

Last note from me — if you're interested but want to see the products before committing, I'd love to send a sample box to {{company}}. No obligation.

Just reply with your shipping address and I'll have it out this week.

Thanks for your time,
Clark""",
            "delay_days": 12,
        },
    ],
}

# ─────────────────────────────────────────────────────
# OUTDOOR / SPORTING / CO-OP sequences
# ─────────────────────────────────────────────────────

OUTDOOR_SEQUENCE = {
    "campaign_name": "ADK Wholesale — Outdoor, Sporting & Co-ops",
    "steps": [
        {
            "subject": "Natural outdoor products from the Adirondacks",
            "body": """Hi {{first_name}},

I'm Clark Maine — my family has been making natural body care and fragrance products on our Adirondack farm since 1979. We're a certified MWBE business.

I wanted to reach out because I think a few of our products would do well at {{company}} — especially our Bug Armor natural insect repellent and our Adirondack-inspired outdoor candle line. They're made from plants we grow and wildcraft on our farm.

You can browse our wholesale line here:
""" + FAIRE_LINK + """

Or just reply and I'll send the order form your way.

Best,
Clark Maine
Adirondack Fragrance & Flavor Farm
wholesale@adirondackfragrance.com""",
            "delay_days": 0,
        },
        {
            "subject": "Re: Natural outdoor products from the Adirondacks",
            "body": """Hi {{first_name}},

Following up on my last note. Our Bug Armor repellent and Hunter's Bro cologne have been our top wholesale movers with outdoor and co-op shops — customers love that they're plant-based and actually made in the mountains.

We offer keystone pricing and low minimums to make it easy to test.

Full catalog here:
""" + CATALOG_PDF + """

Happy to answer any questions.

Clark""",
            "delay_days": 5,
        },
        {
            "subject": "Quick follow-up from ADK Fragrance",
            "body": """Hi {{first_name}},

Short and sweet — if you'd like to try our products before placing an order, I'm happy to send a complimentary sample box to your shop.

Just reply with your shipping address and I'll get it out.

All the best,
Clark""",
            "delay_days": 12,
        },
    ],
}

# ─────────────────────────────────────────────────────
# Mapping and helper
# ─────────────────────────────────────────────────────

SEQUENCES = {
    "apothecary": APOTHECARY_SEQUENCE,
    "boutique": BOUTIQUE_SEQUENCE,
    "outdoor": OUTDOOR_SEQUENCE,
    "coop": OUTDOOR_SEQUENCE,  # co-ops use the outdoor/co-op variant
}


def get_sequence(store_type: str) -> dict:
    """
    Return the sequence dict for a store type.
    Falls back to boutique if type is unknown.
    """
    key = store_type.lower().strip()
    return SEQUENCES.get(key, BOUTIQUE_SEQUENCE)


def classify_store_type(company: str) -> str:
    """
    Guess store type from company name. Returns one of:
    apothecary, boutique, outdoor, coop
    """
    name = company.lower()
    apothecary_words = ["apothecary", "botanical", "naturals", "herbal", "wellness",
                        "natural beauty", "body care", "aromatherapy", "chandlery"]
    coop_words = ["co-op", "coop", "cooperative", "natural food", "market",
                  "grocer", "grocery"]
    outdoor_words = ["outdoor", "sporting", "adventure", "hunting", "fishing",
                     "camping", "hardware", "outfitter"]

    for w in apothecary_words:
        if w in name:
            return "apothecary"
    for w in coop_words:
        if w in name:
            return "coop"
    for w in outdoor_words:
        if w in name:
            return "outdoor"
    return "boutique"


if __name__ == "__main__":
    # Preview all sequences
    for stype, seq in [("apothecary", APOTHECARY_SEQUENCE),
                       ("boutique", BOUTIQUE_SEQUENCE),
                       ("outdoor", OUTDOOR_SEQUENCE)]:
        print(f"\n{'='*60}")
        print(f"  {seq['campaign_name']}")
        print(f"{'='*60}")
        for i, step in enumerate(seq["steps"], 1):
            print(f"\n--- Email {i} (Day {step['delay_days']}) ---")
            print(f"Subject: {step['subject']}")
            word_count = len(step["body"].split())
            print(f"Body ({word_count} words):")
            print(step["body"][:200] + "...")
