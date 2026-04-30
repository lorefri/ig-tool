import os
from dotenv import load_dotenv

load_dotenv(override=True)

INSTAGRAM_USERNAME   = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD   = os.getenv("INSTAGRAM_PASSWORD")
INSTAGRAM_SESSION_ID = os.getenv("INSTAGRAM_SESSION_ID")
ANTHROPIC_API_KEY    = os.getenv("ANTHROPIC_API_KEY")

TARGET_PAGES = [p.strip() for p in os.getenv("TARGET_PAGES", "").split(",") if p.strip()]

# ── DM limits ─────────────────────────────────────────────────────────────────
MAX_DM_PER_DAY    = int(os.getenv("MAX_DM_PER_DAY", 15))
MIN_DELAY_SECONDS = int(os.getenv("MIN_DELAY_SECONDS", 45))
MAX_DELAY_SECONDS = int(os.getenv("MAX_DELAY_SECONDS", 180))

# ── Action limits ─────────────────────────────────────────────────────────────
MAX_FOLLOWS_PER_DAY = int(os.getenv("MAX_FOLLOWS_PER_DAY", 20))
MAX_LIKES_PER_DAY   = int(os.getenv("MAX_LIKES_PER_DAY", 30))
MAX_STORIES_PER_DAY = int(os.getenv("MAX_STORIES_PER_DAY", 20))

# ── Strategy ──────────────────────────────────────────────────────────────────
STRATEGY_TYPE        = os.getenv("STRATEGY_TYPE", "recommended")
DAYS_BETWEEN_STEPS   = int(os.getenv("DAYS_BETWEEN_STEPS", 1))
CUSTOM_DO_FOLLOW     = os.getenv("CUSTOM_DO_FOLLOW",     "true").lower()  == "true"
CUSTOM_DO_LIKE_POST  = os.getenv("CUSTOM_DO_LIKE_POST",  "true").lower()  == "true"
CUSTOM_DO_LIKE_STORY = os.getenv("CUSTOM_DO_LIKE_STORY", "false").lower() == "true"
CUSTOM_DO_DM         = os.getenv("CUSTOM_DO_DM",         "true").lower()  == "true"
CUSTOM_DO_UNFOLLOW   = os.getenv("CUSTOM_DO_UNFOLLOW",   "false").lower() == "true"
DAYS_BEFORE_UNFOLLOW = int(os.getenv("DAYS_BEFORE_UNFOLLOW", 7))

# ── Follow-up DM ──────────────────────────────────────────────────────────────
MAX_DM_FOLLOWUPS      = int(os.getenv("MAX_DM_FOLLOWUPS", 1))
DAYS_BEFORE_FOLLOWUP  = int(os.getenv("DAYS_BEFORE_FOLLOWUP", 5))

# ── Target filters ────────────────────────────────────────────────────────────
MIN_FOLLOWERS         = int(os.getenv("MIN_FOLLOWERS", 100))
MAX_FOLLOWERS         = int(os.getenv("MAX_FOLLOWERS", 50000))
MIN_POSTS             = int(os.getenv("MIN_POSTS", 6))
SKIP_VERIFIED         = os.getenv("SKIP_VERIFIED", "true").lower() == "true"
REQUIRE_ITALY         = os.getenv("REQUIRE_ITALY", "true").lower() == "true"
BIO_INCLUDE_KEYWORDS  = [k.strip().lower() for k in os.getenv("BIO_INCLUDE_KEYWORDS", "").split(",") if k.strip()]
BIO_EXCLUDE_KEYWORDS  = [k.strip().lower() for k in os.getenv("BIO_EXCLUDE_KEYWORDS", "collaborazioni,brand,sponsor,agenzia,agency").split(",") if k.strip()]

# ── Schedule ──────────────────────────────────────────────────────────────────
ACTIVE_HOURS_START = int(os.getenv("ACTIVE_HOURS_START", 9))
ACTIVE_HOURS_END   = int(os.getenv("ACTIVE_HOURS_END", 21))
ACTIVE_DAYS        = [int(d) for d in os.getenv("ACTIVE_DAYS", "1,2,3,4,5,6,7").split(",") if d.strip()]

# ── Messages ──────────────────────────────────────────────────────────────────
MESSAGE_TONE       = os.getenv("MESSAGE_TONE", "informale")  # formale | informale | motivazionale
MESSAGE_VARIANTS   = int(os.getenv("MESSAGE_VARIANTS", 2))

# ── Notifications ─────────────────────────────────────────────────────────────
NOTIFY_ON_REPLY    = os.getenv("NOTIFY_ON_REPLY", "false").lower() == "true"
NOTIFY_WEBHOOK     = os.getenv("NOTIFY_WEBHOOK", "")

# ── Objective ─────────────────────────────────────────────────────────────────
OBJECTIVE        = os.getenv("OBJECTIVE", "sponsorizzazione")  # corso | sponsorizzazione | entrambi | custom
OBJECTIVE_CUSTOM = os.getenv("OBJECTIVE_CUSTOM", "")

OBJECTIVE_CONTEXTS = {
    "corso": """
OBIETTIVO: Vendere corsi di formazione certificati WD International University.
Target ideale: persone che vogliono crescere professionalmente, ottenere una certificazione,
cambiare carriera, migliorare le proprie competenze o aggiornarsi nel proprio settore.
Angolo del messaggio: curiosità verso la crescita personale/professionale, non menzionare il corso direttamente.
Qualifica: preferisci chi parla di lavoro, carriera, formazione, studio, obiettivi professionali.
""",
    "sponsorizzazione": """
OBIETTIVO: Trovare collaboratori per la rete di network marketing WD.
Target ideale: persone con mentalità imprenditoriale, che cercano un reddito extra o una nuova opportunità,
ex networker, persone insoddisfatte del proprio lavoro, chi parla di libertà finanziaria o side income.
Angolo del messaggio: opportunità di collaborazione, crescita insieme, non menzionare network marketing o MLM.
Qualifica: preferisci chi parla di business, guadagno extra, imprenditoria, libertà, obiettivi economici.
""",
    "entrambi": """
OBIETTIVO: Sia vendere corsi che trovare collaboratori per la rete WD.
Target ideale: chiunque abbia interesse per crescita personale, professionale o economica.
Angolo del messaggio: flessibile — adattati al profilo. Se sembra ambizioso/imprenditore → collaborazione.
Se sembra interessato alla formazione → corsi. Messaggio neutro che apre la conversazione.
Qualifica: profilo aperto, mentalità positiva, interessato a migliorarsi.
""",
    "custom": ""  # filled dynamically
}

COMPANY_CONTEXT = """
Lavori per WD International University (companywd.com), una piattaforma italiana di formazione online
con corsi certificati dal Ministero dell'Istruzione (MIM). L'azienda offre percorsi di crescita
professionale e personale. Distribuisce i suoi corsi tramite una rete di collaboratori (network marketing).
Stai cercando persone interessate a crescere professionalmente, guadagnare un reddito extra,
o costruire un proprio business nel settore della formazione.
"""
