"""Lightweight English / Hinglish internationalisation for Aster Ops.

Usage
-----
    from app.i18n import t

    st.button(t("home.btn.start"), type="primary")

The current language is stored in ``st.session_state["lang_is_hinglish"]``
(a bool set by the sidebar toggle).  ``t()`` reads it on every call so
translations update instantly when the toggle flips — no rerun needed.

Adding new strings
------------------
Add a key to ``TRANSLATIONS`` with both ``"en"`` and ``"hi"`` values.
If a key is missing its ``"hi"`` entry the English string is used as a
safe fallback.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Translation table
# ---------------------------------------------------------------------------
# "hi" = Hinglish: natural Hindi + English mixing, NOT formal Hindi.
# Keep technical terms (Invoice, Dashboard, API, SKU …) in English.
# ---------------------------------------------------------------------------

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ── Sidebar navigation ──────────────────────────────────────────────────
    "nav.home":       {"en": "✦  Home",                   "hi": "✦  Ghar"},
    "nav.onboarding": {"en": "◎  Onboarding",              "hi": "◎  Shuruat"},
    "nav.dashboard":  {"en": "▦  Business Dashboard",      "hi": "▦  Dashboard"},
    "nav.customers":  {"en": "◌  Customers",               "hi": "◌  Grahak"},
    "nav.products":   {"en": "◇  Products",                "hi": "◇  Maal / Products"},
    "nav.invoices":   {"en": "▤  Invoices",                "hi": "▤  Bill / Invoice"},
    "nav.memory":     {"en": "◒  Business Memory",         "hi": "◒  Yaadaasht"},
    "nav.government": {"en": "⌁  Government Assistant",    "hi": "⌁  Sarkaari Madad"},
    "nav.voice":      {"en": "🎙  Voice Commands",          "hi": "🎙  Bolo Apna Kaam"},
    "nav.settings":   {"en": "⚙  Settings",                "hi": "⚙  Settings"},
    "nav.code":       {"en": "⟨/⟩  View Code",             "hi": "⟨/⟩  Code Dekho"},

    # ── Sidebar chrome ──────────────────────────────────────────────────────
    "sidebar.caption":      {"en": "AI Operations Employee",  "hi": "AI Kaam-Kaji Sahayak"},
    "sidebar.note.heading": {"en": "Build Week MVP",          "hi": "Pehla Kadam"},
    "sidebar.note.body":    {
        "en": "Your business workspace is ready for its first operational workflow.",
        "hi": "Aapka business workspace pehle workflow ke liye taiyaar hai.",
    },
    "sidebar.lang.toggle":  {"en": "🇮🇳  Hinglish mode",      "hi": "🇮🇳  Hinglish mode"},

    # ── BYOK / API key section ──────────────────────────────────────────────
    "byok.heading": {"en": "Bring Your Own Key",            "hi": "Apni API Key Laao"},
    "byok.caption": {
        "en": "Keys are stored in your browser session only. They override environment secrets.",
        "hi": "Keys sirf aapke browser session mein store hoti hain. Yeh environment secrets override karti hain.",
    },
    "byok.btn.save": {"en": "Save Keys",                    "hi": "Keys Save Karo"},
    "byok.dialog.prompt": {
        "en": "Enter your API key to bypass the missing or rate-limited credential:",
        "hi": "Missing ya rate-limited credential bypass karne ke liye apni API key daalo:",
    },
    "byok.error": {
        "en": (
            "Sorry, this secret key is either not present, credits are finished, "
            "or is rate limited. You can bypass this by adding your new API key below."
        ),
        "hi": (
            "Maafi karo — yeh secret key ya toh nahi hai, credits khatam hain, ya rate limited hai. "
            "Neeche apni nayi API key daalo."
        ),
    },
    "byok.label.openai":        {"en": "OpenAI API Key",         "hi": "OpenAI API Key"},
    "byok.label.groq":          {"en": "Groq API Key",           "hi": "Groq API Key"},
    "byok.label.gemini":        {"en": "Gemini API Key",         "hi": "Gemini API Key"},

    # ── Home page ───────────────────────────────────────────────────────────
    "home.eyebrow":  {"en": "Your operations workspace",   "hi": "Aapka kaam-kaaj ka adda"},
    "home.title":    {"en": "Good morning, Alex.",         "hi": "Namaste, Alex."},
    "home.subtitle": {
        "en": "A calm place to see what matters, delegate routine work, and keep your business moving.",
        "hi": "Yahan sab kuch dekho — kaam delegate karo aur business smoothly chalao.",
    },
    "home.card.heading": {
        "en": "Your AI operations employee is standing by.",
        "hi": "Aapka AI assistant taiyaar khada hai.",
    },
    "home.card.body": {
        "en": (
            "Connect your business data during onboarding, then use this workspace to handle "
            "customers, invoices, inventory, and the details worth remembering."
        ),
        "hi": (
            "Onboarding mein apna data connect karo, phir customers, invoices, "
            "inventory — sab yahaan sambhalo."
        ),
    },
    "home.btn.start":           {"en": "Start onboarding",        "hi": "Shuru Karo"},
    "home.status.label":        {"en": "Workspace status",        "hi": "Workspace ki sthiti"},
    "home.status.steps":        {"en": "Onboarding steps completed", "hi": "Onboarding steps poore"},
    "home.glance.title":        {"en": "At a glance",             "hi": "Ek nazar mein"},
    "home.metric.customers":    {"en": "Customers",               "hi": "Grahak"},
    "home.metric.invoices":     {"en": "Open invoices",           "hi": "Khule huye Bills"},
    "home.metric.products":     {"en": "Products tracked",        "hi": "Products tracked"},
    "home.metric.customers.sub":{"en": "Ready when you are",      "hi": "Aap ke liye taiyaar"},
    "home.metric.invoices.sub": {"en": "No action needed",        "hi": "Abhi kuch nahi karna"},
    "home.metric.products.sub": {"en": "Catalogue not connected", "hi": "Catalogue nahin judi"},
    "home.next.title":    {"en": "Suggested next step",           "hi": "Aage kya karna hai"},
    "home.next.primary":  {"en": "Tell us about your business",   "hi": "Apne business ke baare mein batao"},
    "home.next.secondary":{
        "en": "Set your company name, operating currency, and the workflows you want help with.",
        "hi": "Company naam, currency aur kaunse kaam mein madad chahiye — yeh sab batao.",
    },

    # ── Dashboard ───────────────────────────────────────────────────────────
    "dashboard.eyebrow":  {"en": "Live operations",              "hi": "Live kaam-kaaj"},
    "dashboard.title":    {"en": "Business dashboard",           "hi": "Business Dashboard"},
    "dashboard.subtitle": {
        "en": "A focused view of revenue, cash flow, stock, and the work worth your attention today.",
        "hi": "Revenue, cash flow, stock aur aaj ke zaroori kaam — sab ek jagah.",
    },
    "dashboard.empty.title": {
        "en": "Create a workspace to see your dashboard",
        "hi": "Dashboard dekhne ke liye workspace banao",
    },
    "dashboard.empty.body": {
        "en": "Your sales, payments, inventory, and activity will appear here as soon as business data exists.",
        "hi": "Sales, payments, inventory sab yahan aayega jab aap data add karoge.",
    },
    "dashboard.empty.btn":  {"en": "Go to onboarding",           "hi": "Onboarding pe jao"},

    # ── Customers ───────────────────────────────────────────────────────────
    "customers.eyebrow":  {"en": "Customer relationships",       "hi": "Grahak sambandh"},
    "customers.title":    {"en": "Customers, in one place.",     "hi": "Saare Grahak, ek jagah."},
    "customers.subtitle": {
        "en": "Keep the people you serve close at hand. Customer activity and context will live here.",
        "hi": "Jo log aapse kaam karvaate hain — unki poori activity yahan milegi.",
    },
    "customers.btn.add":         {"en": "Add customer",          "hi": "Grahak Add Karo"},
    "customers.search":          {"en": "Search by name or email","hi": "Naam ya email se khojo"},
    "customers.empty.title":     {"en": "Your customer list is empty","hi": "Abhi koi grahak nahin hai"},
    "customers.empty.body":      {
        "en": "Add your first customer to begin building a clearer view of relationships and revenue.",
        "hi": "Pehla grahak add karo aur apna business network banana shuru karo.",
    },
    "customers.empty.btn":       {"en": "Add your first customer","hi": "Pehla Grahak Add Karo"},

    # ── Products ────────────────────────────────────────────────────────────
    "products.eyebrow":  {"en": "Product catalogue",             "hi": "Maal ki list"},
    "products.title":    {"en": "What your business sells.",     "hi": "Aap kya bechte hain."},
    "products.subtitle": {
        "en": "Build a simple, reliable view of products, suppliers, pricing, and stock positions.",
        "hi": "Products, suppliers, daam aur stock — sab clearly dekho.",
    },
    "products.btn.add":    {"en": "Add product",                 "hi": "Maal Add Karo"},
    "products.search":     {"en": "Search products or SKUs",     "hi": "Products ya SKU se khojo"},
    "products.empty.title":{"en": "No products yet",             "hi": "Abhi koi product nahin hai"},
    "products.empty.body": {
        "en": "Create a product to establish your catalogue and start tracking operational inventory.",
        "hi": "Pehla product add karo aur apna catalogue banana shuru karo.",
    },
    "products.empty.btn":  {"en": "Create a product",            "hi": "Product Banao"},

    # ── Invoices ────────────────────────────────────────────────────────────
    "invoices.eyebrow":  {"en": "Invoices",                      "hi": "Bill / Invoice"},
    "invoices.title":    {"en": "Keep cash flow in view.",       "hi": "Paisa aana-jaana track karo."},
    "invoices.subtitle": {
        "en": "Review invoices and download them as JPG or AVIF images for sharing or archiving.",
        "hi": "Invoices dekho aur JPG ya AVIF mein download karo — share ya store karo.",
    },
    "invoices.btn.create": {"en": "Create invoice",              "hi": "Invoice Banao"},

    # ── Onboarding ──────────────────────────────────────────────────────────
    "onboarding.eyebrow":  {"en": "Workspace setup",             "hi": "Workspace taiyaar karo"},
    "onboarding.title":    {"en": "Let's make this feel like your business.", "hi": "Isko apna business bana do."},
    "onboarding.subtitle": {
        "en": "Create your business workspace, then review exactly what will be imported before anything is saved.",
        "hi": "Apna business workspace banao, phir import se pehle sab check karo.",
    },

    # ── Voice Commands ──────────────────────────────────────────────────────
    "voice.eyebrow":  {"en": "Voice commands",                   "hi": "Bolke Kaam Karwao"},
    "voice.title":    {"en": "Talk to your operations employee.", "hi": "Apne AI se baat karo."},
    "voice.subtitle": {
        "en": "Speak in English or Hindi — create invoices, add customers, update stock, set reminders.",
        "hi": "Hindi ya English mein bolo — invoice banao, customer add karo, stock update karo.",
    },
    "voice.section.input":      {"en": "Voice input",            "hi": "Awaaz se input"},
    "voice.label.record":       {"en": "🎙 Record your command",  "hi": "🎙 Apna command bolo"},
    "voice.help.record":        {
        "en": "Supports English and Hindi · e.g. \"Create an invoice for Acme Corp for $500\"",
        "hi": "English aur Hindi supported · jaise \"Acme Corp ke liye ₹500 ka invoice banao\"",
    },
    "voice.btn.run":            {"en": "▶ Run command",          "hi": "▶ Command chalao"},
    "voice.section.history":    {"en": "Command history",        "hi": "Command history"},
    "voice.section.examples":   {"en": "Example commands",       "hi": "Example commands"},
    "voice.spinner.working":    {"en": "Working on it…",         "hi": "Kaam chal raha hai…"},
    "voice.error.command":      {"en": "Command failed",         "hi": "Command fail ho gayi"},
    "voice.error.workspace":    {"en": "Could not load workspaces", "hi": "Workspaces load nahin ho saki"},
    "voice.empty.heading":      {"en": "Get started",            "hi": "Shuru karo"},
    "voice.empty.title":        {"en": "Create your workspace first", "hi": "Pehle workspace banao"},
    "voice.empty.body":         {
        "en": "Once your business is set up you can come back here and speak commands like \"Create an invoice for ₹5,000\" or \"Add a new customer\".",
        "hi": "Jab aapka business set ho jayega toh yahan aake \"₹5,000 ka invoice banao\" ya \"Naya customer add karo\" jaise commands bol sakte ho.",
    },
    "voice.empty.prompt":       {
        "en": "Complete onboarding to enable voice commands. Head to **Onboarding** in the sidebar to create your business workspace.",
        "hi": "Voice commands enable karne ke liye onboarding complete karo. Sidebar mein **Onboarding** pe jao aur apna business workspace banao.",
    },
    "voice.label.workspace":    {"en": "Workspace",              "hi": "Workspace"},

    # ── Government Assistant ────────────────────────────────────────────────
    "gov.eyebrow":  {"en": "Government assistant",               "hi": "Sarkaari madad"},
    "gov.title":    {"en": "Prepare your next registration step.","hi": "Agle registration step ki taiyaari karo."},
    "gov.subtitle": {
        "en": "General information and official links for India and the United States — not legal or tax advice.",
        "hi": "India aur US ke liye general jankari aur official links — yeh legal ya tax advice nahin hai.",
    },

    # ── Business Memory ─────────────────────────────────────────────────────
    "memory.eyebrow":  {"en": "Business memory",                 "hi": "Business ki yaadaasht"},
    "memory.title":    {"en": "The details worth remembering.",  "hi": "Woh baatein jo yaad rakhni chahiye."},
    "memory.subtitle": {
        "en": "A transparent home for the facts, preferences, and operational context your AI employee will use.",
        "hi": "Facts, preferences aur kaam ka context — AI yahan se padh ke smarter hota hai.",
    },

    # ── Settings ────────────────────────────────────────────────────────────
    "settings.eyebrow":  {"en": "Settings",                      "hi": "Settings"},
    "settings.title":    {"en": "Make the workspace yours.",     "hi": "Workspace ko apna banao."},
    "settings.subtitle": {
        "en": "Manage your business profile, notifications, and the preferences that shape future operations support.",
        "hi": "Business profile, notifications aur preferences manage karo.",
    },
    "settings.section.profile": {"en": "Business profile",      "hi": "Business ki jankari"},
    "settings.section.notif":   {"en": "Notifications",         "hi": "Suchnaayein"},
    "settings.btn.save":        {"en": "Save preferences",       "hi": "Preferences Save Karo"},
    "settings.label.biz_name":  {"en": "Business name",          "hi": "Business ka naam"},
    "settings.ph.biz_name":     {"en": "Your business name",     "hi": "Aapke business ka naam"},
    "settings.label.biz_email": {"en": "Business email",         "hi": "Business email"},
    "settings.ph.biz_email":    {"en": "you@company.com",        "hi": "aap@company.com"},
    "settings.label.currency":  {"en": "Default currency",       "hi": "Default currency"},
    "settings.opt.currency.usd":{"en": "USD — US Dollar",        "hi": "USD — US Dollar"},
    "settings.opt.currency.eur":{"en": "EUR — Euro",             "hi": "EUR — Euro"},
    "settings.opt.currency.inr":{"en": "INR — Indian Rupee",     "hi": "INR — Indian Rupee"},
    "settings.label.timezone":  {"en": "Time zone",              "hi": "Time zone"},
    "settings.opt.tz.kolkata":  {"en": "Asia/Kolkata",           "hi": "Asia/Kolkata"},
    "settings.opt.tz.london":   {"en": "Europe/London",          "hi": "Europe/London"},
    "settings.opt.tz.newyork":  {"en": "America/New_York",       "hi": "America/New_York"},
    "settings.toggle.summary":  {"en": "Operational summaries",  "hi": "Operational summaries"},
    "settings.help.summary":    {
        "en": "A future summary of business activity.",
        "hi": "Business activity ka future summary.",
    },
    "settings.toggle.alerts":   {"en": "Attention-needed alerts","hi": "Dhyaan chahiye alerts"},
    "settings.help.alerts":     {
        "en": "A future alert for items requiring review.",
        "hi": "Review chahiye items ke liye future alert.",
    },

    # ── Code Viewer ─────────────────────────────────────────────────────────
    "code.eyebrow":  {"en": "Source",                            "hi": "Source"},
    "code.title":    {"en": "View Code",                         "hi": "Code Dekho"},
    "code.subtitle": {
        "en": "Browse every file in the project — search by name or content, then expand to read.",
        "hi": "Project ke saare files dekho — naam ya content se khojo, phir expand karke padho.",
    },
}


def t(key: str) -> str:
    """Return the UI string for *key* in the currently selected language.

    Falls back to English if the Hinglish translation is missing,
    and to the raw key if the key itself is not found.
    """
    lang: str = "hi" if st.session_state.get("lang_is_hinglish", False) else "en"
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key  # unknown key — surface it so it is easy to spot
    return entry.get(lang) or entry.get("en") or key
