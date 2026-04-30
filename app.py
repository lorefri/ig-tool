import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import dotenv_values, set_key

from tool_runner import start_tool, stop_tool, is_running, get_logs

ENV_FILE      = str(Path(__file__).parent / ".env")
CONTACTS_FILE = Path(__file__).parent / "contacts.json"

st.set_page_config(page_title="WD Outreach", page_icon="⚡", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:linear-gradient(160deg,#070714 0%,#0d0d2b 60%,#070714 100%);color:#e2e8f0;}
section[data-testid="stSidebar"]{background:rgba(10,10,35,0.97)!important;border-right:1px solid rgba(124,58,237,0.2);}
section[data-testid="stSidebar"] *{color:#c4c9e2!important;}
.card{background:rgba(255,255,255,0.03);border:1px solid rgba(124,58,237,0.2);border-radius:18px;
      padding:28px 24px;text-align:center;backdrop-filter:blur(12px);transition:all 0.3s ease;margin-bottom:8px;}
.card:hover{border-color:rgba(124,58,237,0.5);background:rgba(124,58,237,0.07);transform:translateY(-3px);
            box-shadow:0 8px 32px rgba(124,58,237,0.15);}
.card-value{font-size:2.6rem;font-weight:700;background:linear-gradient(135deg,#a78bfa,#60a5fa);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1.1;}
.card-label{font-size:0.76rem;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;color:#8892b0!important;margin-top:8px;}
.card-reply{border-color:rgba(16,185,129,0.4)!important;background:rgba(16,185,129,0.05)!important;}
.card-reply .card-value{background:linear-gradient(135deg,#34d399,#10b981);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.section-title{font-size:1.3rem;font-weight:700;color:#e2e8f0;margin-bottom:20px;padding-bottom:10px;border-bottom:1px solid rgba(124,58,237,0.2);}
.tag{display:inline-flex;align-items:center;background:rgba(124,58,237,0.12);border:1px solid rgba(124,58,237,0.3);border-radius:20px;padding:5px 14px;margin:3px;font-size:0.83rem;color:#a78bfa;}
.log-box{background:rgba(0,0,0,0.5);border:1px solid rgba(124,58,237,0.15);border-radius:12px;padding:16px;
         font-family:'Courier New',monospace;font-size:0.77rem;color:#94a3b8;max-height:440px;overflow-y:auto;line-height:1.7;white-space:pre-wrap;}
.status-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px;}
.dot-green{background:#10b981;box-shadow:0 0 7px #10b981;animation:pulse 1.5s infinite;}
.dot-grey{background:#475569;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.35;}}
.logo-box{background:linear-gradient(135deg,rgba(124,58,237,0.18),rgba(59,130,246,0.18));border:1px solid rgba(124,58,237,0.3);border-radius:16px;padding:18px;text-align:center;margin-bottom:24px;}
.logo-title{font-size:1.2rem;font-weight:700;background:linear-gradient(135deg,#a78bfa,#60a5fa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.logo-sub{font-size:0.72rem;color:#8892b0;margin-top:3px;}
.flow-step{background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.25);border-radius:14px;padding:18px 16px;text-align:center;}
.flow-step-day{font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;color:#8892b0;margin-bottom:6px;}
.flow-step-icon{font-size:1.8rem;margin-bottom:6px;}
.flow-step-title{font-size:0.88rem;font-weight:600;color:#a78bfa;}
.flow-step-desc{font-size:0.75rem;color:#8892b0;margin-top:4px;}
.flow-arrow{display:flex;align-items:center;justify-content:center;font-size:1.4rem;color:rgba(124,58,237,0.5);}
.dm-card{background:rgba(255,255,255,0.02);border:1px solid rgba(124,58,237,0.12);border-radius:12px;padding:14px 16px;margin-bottom:8px;}
.reply-card{border-color:rgba(16,185,129,0.3)!important;background:rgba(16,185,129,0.04)!important;}
.dm-user{font-weight:600;color:#a78bfa;font-size:0.88rem;}
.dm-user-reply{color:#34d399!important;}
.dm-msg{font-size:0.78rem;color:#8892b0;margin-top:5px;line-height:1.5;}
.dm-time{font-size:0.68rem;color:#475569;margin-top:6px;}
.section-header{font-weight:600;color:#c4c9e2;margin-bottom:14px;font-size:0.82rem;letter-spacing:0.06em;text-transform:uppercase;}
div.stButton>button{background:linear-gradient(135deg,#7c3aed,#2563eb);color:white;border:none;border-radius:10px;font-weight:600;font-size:0.88rem;transition:all 0.2s;width:100%;}
div.stButton>button:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(124,58,237,0.4);}
.stTextInput>div>div>input,.stNumberInput>div>div>input,.stTextArea>div>div>textarea{background:rgba(255,255,255,0.04)!important;border:1px solid rgba(124,58,237,0.25)!important;border-radius:10px!important;color:#e2e8f0!important;}
.stSelectbox>div>div{background:rgba(255,255,255,0.04)!important;border:1px solid rgba(124,58,237,0.25)!important;border-radius:10px!important;}
div[data-testid="stDataFrame"]{border-radius:12px;overflow:hidden;}
hr{border-color:rgba(124,58,237,0.12)!important;}
.active-badge{display:inline-block;padding:3px 12px;border-radius:20px;font-size:0.73rem;font-weight:600;background:rgba(16,185,129,0.15);color:#34d399;border:1px solid rgba(16,185,129,0.3);}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def load_contacts():
    if not CONTACTS_FILE.exists(): return {}
    return json.loads(CONTACTS_FILE.read_text(encoding="utf-8"))

def load_env(): return dotenv_values(ENV_FILE)
def save_env_key(k, v): set_key(ENV_FILE, k, v)

def get_target_pages():
    raw = load_env().get("TARGET_PAGES","")
    return [p.strip() for p in raw.split(",") if p.strip()]

def save_target_pages(pages): save_env_key("TARGET_PAGES", ",".join(pages))

def contacts_stats(c):
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "dm_total":   sum(1 for d in c.values() if d.get("status") == "dm_sent"),
        "dm_today":   sum(1 for d in c.values() if d.get("status") == "dm_sent" and d.get("timestamp","").startswith(today)),
        "replied":    sum(1 for d in c.values() if d.get("status") == "replied"),
        "warming":    sum(1 for d in c.values() if d.get("stage") in ("new","followed","liked_post","liked_story")),
        "not_target": sum(1 for d in c.values() if d.get("status") == "not_target"),
        "total":      len(c),
    }


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="logo-box"><div class="logo-title">⚡ WD Outreach</div><div class="logo-sub">Instagram AI Tool</div></div>', unsafe_allow_html=True)
    running = is_running()
    dot = "dot-green" if running else "dot-grey"
    txt = "In esecuzione" if running else "Fermo"
    st.markdown(f'<div style="display:flex;align-items:center;margin-bottom:20px;padding:12px;background:rgba(255,255,255,0.03);border-radius:10px;border:1px solid rgba(124,58,237,0.15)"><span class="status-dot {dot}"></span><span style="font-size:0.85rem;font-weight:500">{txt}</span></div>', unsafe_allow_html=True)
    nav = st.radio("Menu", ["🏠  Dashboard","🎯  Pagine Target","🏹  Obiettivo","🧠  Strategia","▶️  Controllo","👥  Contatti","⚙️  Impostazioni"], label_visibility="collapsed")

page = nav.split("  ")[1]


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    contacts = load_contacts()
    s = contacts_stats(contacts)
    env = load_env()

    st.markdown('<div class="section-title">Dashboard</div>', unsafe_allow_html=True)

    cols = st.columns(6)
    items = [
        ("dm_today",   "DM oggi",           False),
        ("dm_total",   "DM totali",          False),
        ("replied",    "Risposte ricevute",  True),
        ("warming",    "In sequenza",        False),
        ("not_target", "Non in target",      False),
        ("total",      "Profili analizzati", False),
    ]
    for col, (key, label, is_reply) in zip(cols, items):
        with col:
            extra = ' card-reply' if is_reply else ''
            st.markdown(f'<div class="card{extra}"><div class="card-value">{s[key]}</div><div class="card-label">{label}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_r = st.columns([1.6, 1])

    with col_l:
        # Risposte ricevute (priorità)
        replied = [(u,d) for u,d in contacts.items() if d.get("status")=="replied"]
        if replied:
            st.markdown('<div class="section-header" style="color:#34d399">💬 RISPOSTE RICEVUTE — DA CONTATTARE</div>', unsafe_allow_html=True)
            replied.sort(key=lambda x: x[1].get("reply_date",""), reverse=True)
            for u,d in replied[:4]:
                st.markdown(f'<div class="dm-card reply-card"><div class="dm-user dm-user-reply">✅ @{u}</div><div class="dm-msg">Ha risposto al tuo DM — contattalo su WhatsApp!</div><div class="dm-time">{d.get("reply_date","")}</div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<div class="section-header">ULTIMI DM INVIATI</div>', unsafe_allow_html=True)
        sent = [(u,d) for u,d in contacts.items() if d.get("status")=="dm_sent"]
        sent.sort(key=lambda x: x[1].get("timestamp",""), reverse=True)
        if sent:
            for u,d in sent[:6]:
                msg = d.get("message","")
                st.markdown(f'<div class="dm-card"><div class="dm-user">@{u}</div><div class="dm-msg">{msg[:130]}{"..." if len(msg)>130 else ""}</div><div class="dm-time">{d.get("timestamp","")}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#475569;font-size:0.88rem">Nessun DM inviato ancora.</p>', unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="section-header">PAGINE TARGET</div>', unsafe_allow_html=True)
        for p in get_target_pages():
            st.markdown(f'<div class="tag">@{p}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">STRATEGIA ATTIVA</div>', unsafe_allow_html=True)
        strat = env.get("STRATEGY_TYPE","recommended")
        label = "⭐ Consigliata (Multi-touch)" if strat=="recommended" else "🛠️ Personalizzata"
        st.markdown(f'<div style="background:rgba(124,58,237,0.1);border:1px solid rgba(124,58,237,0.3);border-radius:10px;padding:12px 16px;color:#a78bfa;font-weight:600;font-size:0.88rem">{label}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">TONO MESSAGGI</div>', unsafe_allow_html=True)
        tone = env.get("MESSAGE_TONE","informale").capitalize()
        st.markdown(f'<div style="background:rgba(96,165,250,0.08);border:1px solid rgba(96,165,250,0.2);border-radius:10px;padding:10px 14px;color:#60a5fa;font-size:0.85rem">💬 {tone}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGINE TARGET
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Pagine Target":
    st.markdown('<div class="section-title">🎯 Pagine Target</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8892b0;font-size:0.88rem;margin-bottom:24px">I follower di queste pagine verranno analizzati dall\'AI. Scegli pagine italiane molto specifiche: guadagno online, network marketing, crescita personale, formazione professionale, imprenditoria.</p>', unsafe_allow_html=True)

    pages_list = get_target_pages()
    st.markdown('<div class="section-header">PAGINE ATTIVE</div>', unsafe_allow_html=True)
    if pages_list:
        for i,p in enumerate(pages_list):
            c1,c2 = st.columns([6,1])
            with c1: st.markdown(f'<div class="tag">@{p}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("✕", key=f"del_{i}"):
                    pages_list.pop(i); save_target_pages(pages_list); st.rerun()
    else:
        st.markdown('<p style="color:#475569;font-size:0.85rem">Nessuna pagina configurata.</p>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">AGGIUNGI PAGINA</div>', unsafe_allow_html=True)
    c1,c2 = st.columns([4,1])
    with c1: new_page = st.text_input("", placeholder="es. networkmarketingitalia", label_visibility="collapsed")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Aggiungi"):
            clean = new_page.strip().lstrip("@")
            if clean and clean not in pages_list:
                pages_list.append(clean); save_target_pages(pages_list); st.success(f"@{clean} aggiunta!"); st.rerun()
            elif clean in pages_list: st.warning("Già presente.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 **Consiglio:** 3-5 pagine italiane molto specifiche per il tuo target danno risultati molto migliori di tante pagine generiche.")


# ══════════════════════════════════════════════════════════════════════════════
# OBIETTIVO
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Obiettivo":
    st.markdown('<div class="section-title">🏹 Obiettivo</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8892b0;font-size:0.88rem;margin-bottom:28px">Scegli cosa vuoi ottenere. Claude adatterà automaticamente chi cercare, come qualificare i profili e il tono dei messaggi in base all\'obiettivo selezionato.</p>', unsafe_allow_html=True)

    env = load_env()
    current_obj = env.get("OBJECTIVE", "sponsorizzazione")

    OBJECTIVES = {
        "sponsorizzazione": {
            "icon": "🤝",
            "title": "Sponsorizzazione",
            "desc": "Cerchi collaboratori per la rete WD",
            "detail": "Target: persone con mentalità imprenditoriale, side income, libertà finanziaria. Messaggio: opportunità di collaborazione e crescita insieme.",
            "color": "#a78bfa"
        },
        "corso": {
            "icon": "🎓",
            "title": "Vendi un Corso",
            "desc": "Vuoi vendere corsi di formazione WD",
            "detail": "Target: persone che vogliono crescere professionalmente, cambiare carriera, ottenere certificazioni. Messaggio: curiosità verso la crescita personale.",
            "color": "#60a5fa"
        },
        "entrambi": {
            "icon": "⚡",
            "title": "Entrambi",
            "desc": "Sia corsi che collaboratori",
            "detail": "Target ampio: chiunque abbia interesse per crescita personale, professionale o economica. Claude adatta il messaggio al profilo specifico.",
            "color": "#34d399"
        },
        "custom": {
            "icon": "✏️",
            "title": "Personalizzato",
            "desc": "Definisci tu l'obiettivo",
            "detail": "Scrivi il tuo obiettivo personalizzato e Claude lo userà come riferimento per qualificazione e messaggi.",
            "color": "#f59e0b"
        },
    }

    c1, c2, c3, c4 = st.columns(4)
    for col, (key, obj) in zip([c1,c2,c3,c4], OBJECTIVES.items()):
        with col:
            is_active = current_obj == key
            border = f"2px solid {obj['color']}" if is_active else f"1px solid rgba(124,58,237,0.2)"
            bg = f"rgba(124,58,237,0.08)" if is_active else "rgba(255,255,255,0.02)"
            badge = f'<div style="display:inline-block;padding:2px 10px;background:{obj["color"]}22;color:{obj["color"]};border-radius:20px;font-size:0.7rem;font-weight:600;margin-top:8px">{"✅ ATTIVO" if is_active else ""}</div>' if is_active else ""
            st.markdown(f"""
            <div style="background:{bg};border:{border};border-radius:16px;padding:22px 16px;text-align:center;min-height:160px">
                <div style="font-size:2rem;margin-bottom:8px">{obj['icon']}</div>
                <div style="font-weight:700;color:#e2e8f0;font-size:0.95rem">{obj['title']}</div>
                <div style="color:#8892b0;font-size:0.78rem;margin-top:6px">{obj['desc']}</div>
                {badge}
            </div>
            """, unsafe_allow_html=True)
            if not is_active:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(f"Seleziona", key=f"obj_{key}"):
                    save_env_key("OBJECTIVE", key)
                    st.success(f"Obiettivo impostato: {obj['title']}"); st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Dettaglio obiettivo attivo
    active = OBJECTIVES[current_obj]
    st.markdown(f"""
    <div style="background:rgba(124,58,237,0.06);border:1px solid rgba(124,58,237,0.2);border-radius:14px;padding:20px 24px">
        <div style="font-size:0.82rem;font-weight:600;color:#a78bfa;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:10px">
            {active['icon']} OBIETTIVO ATTIVO — {active['title'].upper()}
        </div>
        <div style="color:#c4c9e2;font-size:0.88rem;line-height:1.7">{active['detail']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Campo custom
    if current_obj == "custom":
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">DESCRIVI IL TUO OBIETTIVO</div>', unsafe_allow_html=True)
        custom_text = st.text_area(
            "", value=env.get("OBJECTIVE_CUSTOM",""),
            placeholder="Es: Cerco persone interessate a diventare trainer/coach nel settore della formazione aziendale...",
            height=120, label_visibility="collapsed"
        )
        if st.button("💾 Salva obiettivo personalizzato"):
            save_env_key("OBJECTIVE_CUSTOM", custom_text)
            st.success("Salvato! Claude userà questo obiettivo per qualificare i profili e scrivere i messaggi.")


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGIA
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Strategia":
    st.markdown('<div class="section-title">🧠 Strategia di Outreach</div>', unsafe_allow_html=True)
    env = load_env()
    current = env.get("STRATEGY_TYPE","recommended")

    tab1, tab2 = st.tabs(["⭐ Strategia Consigliata", "🛠️ Strategia Personalizzata"])

    with tab1:
        if current == "recommended":
            st.markdown('<div class="active-badge">✅ Attiva</div><br><br>', unsafe_allow_html=True)
        st.markdown('<p style="color:#8892b0;font-size:0.88rem;margin-bottom:24px">L\'AI interagisce con il profilo per più giorni prima del DM. La persona ti conosce già quando riceve il messaggio — tassi di risposta molto più alti.</p>', unsafe_allow_html=True)

        c1,a1,c2,a2,c3,a3,c4 = st.columns([2,.35,2,.35,2,.35,2])
        with c1: st.markdown('<div class="flow-step"><div class="flow-step-day">Scoperta</div><div class="flow-step-icon">🔍</div><div class="flow-step-title">Profilo trovato</div><div class="flow-step-desc">AI analizza e qualifica</div></div>', unsafe_allow_html=True)
        with a1: st.markdown('<div class="flow-arrow" style="padding-top:38px">→</div>', unsafe_allow_html=True)
        with c2: st.markdown('<div class="flow-step"><div class="flow-step-day">Giorno 1</div><div class="flow-step-icon">👤❤️</div><div class="flow-step-title">Follow + Like post</div><div class="flow-step-desc">Prima interazione naturale</div></div>', unsafe_allow_html=True)
        with a2: st.markdown('<div class="flow-arrow" style="padding-top:38px">→</div>', unsafe_allow_html=True)
        with c3: st.markdown('<div class="flow-step"><div class="flow-step-day">Giorno 2</div><div class="flow-step-icon">👁️</div><div class="flow-step-title">Like storia</div><div class="flow-step-desc">Visibilità aggiuntiva</div></div>', unsafe_allow_html=True)
        with a3: st.markdown('<div class="flow-arrow" style="padding-top:38px">→</div>', unsafe_allow_html=True)
        with c4: st.markdown('<div class="flow-step"><div class="flow-step-day">Giorno 3</div><div class="flow-step-icon">💬</div><div class="flow-step-title">DM personalizzato</div><div class="flow-step-desc">Messaggio AI su misura</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        days = st.slider("Giorni di attesa tra ogni step", 1, 3, int(env.get("DAYS_BETWEEN_STEPS","1")))
        if st.button("✅ Attiva Strategia Consigliata"):
            save_env_key("STRATEGY_TYPE","recommended"); save_env_key("DAYS_BETWEEN_STEPS",str(days))
            st.success("Attivata!"); st.rerun()

    with tab2:
        if current == "custom":
            st.markdown('<div class="active-badge">✅ Attiva</div><br><br>', unsafe_allow_html=True)

        st.markdown('<p style="color:#8892b0;font-size:0.88rem;margin-bottom:20px">Costruisci la tua sequenza scegliendo quali azioni eseguire e con quali tempistiche.</p>', unsafe_allow_html=True)

        cl, cr = st.columns(2)
        with cl:
            st.markdown('<div class="section-header">AZIONI IN SEQUENZA</div>', unsafe_allow_html=True)
            do_follow      = st.checkbox("👤 Segui il profilo",          value=env.get("CUSTOM_DO_FOLLOW","true")=="true")
            do_like_post   = st.checkbox("❤️  Like al post recente",      value=env.get("CUSTOM_DO_LIKE_POST","true")=="true")
            do_like_story  = st.checkbox("👁️  Like alla storia",          value=env.get("CUSTOM_DO_LIKE_STORY","false")=="true")
            do_dm          = st.checkbox("💬 Invia DM personalizzato",   value=env.get("CUSTOM_DO_DM","true")=="true")

            st.markdown('<div class="section-header" style="margin-top:20px">GESTIONE FOLLOW</div>', unsafe_allow_html=True)
            do_unfollow = st.checkbox("🔕 Unfollow chi non ricambia dopo X giorni", value=env.get("CUSTOM_DO_UNFOLLOW","false")=="true")
            days_unfollow = st.number_input("Giorni prima di unfollow", 3, 30, int(env.get("DAYS_BEFORE_UNFOLLOW","7")), disabled=not do_unfollow)

        with cr:
            st.markdown('<div class="section-header">TEMPISTICHE</div>', unsafe_allow_html=True)
            days_between = st.number_input("Giorni tra ogni step", 0, 7, int(env.get("DAYS_BETWEEN_STEPS","1")))

            st.markdown('<div class="section-header" style="margin-top:20px">FOLLOW-UP AUTOMATICI</div>', unsafe_allow_html=True)
            max_followups   = st.number_input("Numero max follow-up", 0, 3, int(env.get("MAX_DM_FOLLOWUPS","1")), help="0 = disabilitato")
            days_followup   = st.number_input("Giorni prima del follow-up", 3, 14, int(env.get("DAYS_BEFORE_FOLLOWUP","5")), disabled=max_followups==0)

            st.markdown('<div class="section-header" style="margin-top:20px">LIMITI GIORNALIERI</div>', unsafe_allow_html=True)
            max_follows  = st.number_input("Max follow/giorno",  5, 50, int(env.get("MAX_FOLLOWS_PER_DAY","20")))
            max_likes    = st.number_input("Max like/giorno",    5, 80, int(env.get("MAX_LIKES_PER_DAY","30")))
            max_stories  = st.number_input("Max storie/giorno",  5, 50, int(env.get("MAX_STORIES_PER_DAY","20")))

        if st.button("🛠️ Attiva Strategia Personalizzata"):
            for k,v in [("STRATEGY_TYPE","custom"),("CUSTOM_DO_FOLLOW",str(do_follow).lower()),
                        ("CUSTOM_DO_LIKE_POST",str(do_like_post).lower()),("CUSTOM_DO_LIKE_STORY",str(do_like_story).lower()),
                        ("CUSTOM_DO_DM",str(do_dm).lower()),("CUSTOM_DO_UNFOLLOW",str(do_unfollow).lower()),
                        ("DAYS_BETWEEN_STEPS",str(days_between)),("DAYS_BEFORE_UNFOLLOW",str(days_unfollow)),
                        ("MAX_DM_FOLLOWUPS",str(max_followups)),("DAYS_BEFORE_FOLLOWUP",str(days_followup)),
                        ("MAX_FOLLOWS_PER_DAY",str(max_follows)),("MAX_LIKES_PER_DAY",str(max_likes)),
                        ("MAX_STORIES_PER_DAY",str(max_stories))]:
                save_env_key(k,v)
            st.success("Attivata!"); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# CONTROLLO
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Controllo":
    st.markdown('<div class="section-title">▶️ Controllo Tool</div>', unsafe_allow_html=True)
    running = is_running()
    _,col,_ = st.columns([1,2,1])
    with col:
        if running:
            st.markdown('<div style="text-align:center;padding:24px 0"><div style="font-size:2.8rem">⚡</div><div style="font-size:1.3rem;font-weight:700;color:#34d399;margin:10px 0"><span class="status-dot dot-green"></span>In esecuzione</div><div style="color:#8892b0;font-size:0.83rem">Sta analizzando profili e avanzando le sequenze</div></div>', unsafe_allow_html=True)
            if st.button("⏹  Ferma Tool"):
                stop_tool(); st.success("Fermato."); st.rerun()
        else:
            st.markdown('<div style="text-align:center;padding:24px 0"><div style="font-size:2.8rem">🚀</div><div style="font-size:1.3rem;font-weight:700;color:#94a3b8;margin:10px 0">Tool fermo</div><div style="color:#8892b0;font-size:0.83rem">Avvia per iniziare la sessione di oggi</div></div>', unsafe_allow_html=True)
            env = load_env()
            start_h = int(env.get("ACTIVE_HOURS_START","9"))
            end_h   = int(env.get("ACTIVE_HOURS_END","21"))
            ora = datetime.now().hour
            if ora < start_h or ora >= end_h:
                st.warning(f"⏰ Fuori orario configurato ({start_h}:00–{end_h}:00).")
            if not get_target_pages():
                st.error("⚠️ Aggiungi almeno una pagina target.")
            else:
                if st.button("▶️  Avvia Tool"):
                    start_tool(); st.success("Avviato!"); st.rerun()

    st.markdown("---")
    ch, cb = st.columns([5,1])
    with ch: st.markdown('<div class="section-header">LOG IN TEMPO REALE</div>', unsafe_allow_html=True)
    with cb:
        if st.button("↻"): st.rerun()

    logs = get_logs(100)
    if logs:
        colored = ""
        for line in logs.splitlines():
            if any(x in line for x in ("✓","Login","Avviato","completata")):
                colored += f'<span style="color:#34d399">{line}</span>\n'
            elif any(x in line for x in ("Errore","Error","Traceback")):
                colored += f'<span style="color:#f87171">{line}</span>\n'
            elif "non in target" in line or "filtrato" in line:
                colored += f'<span style="color:#334155">{line}</span>\n'
            elif any(x in line for x in ("in target","DM inviato","Seguito","Like","storia","Risposta","Follow-up")):
                colored += f'<span style="color:#a78bfa">{line}</span>\n'
            elif any(x in line for x in ("Scansione","Trovati","Analisi","Strategia","sequenza","nuovi","Controllo","Unfollow")):
                colored += f'<span style="color:#60a5fa">{line}</span>\n'
            else:
                colored += f'{line}\n'
        st.markdown(f'<div class="log-box">{colored}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="log-box" style="color:#475569;text-align:center;padding:50px">Nessun log. Avvia il tool per vedere l\'attività.</div>', unsafe_allow_html=True)

    if running:
        import time; time.sleep(3); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# CONTATTI
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Contatti":
    contacts = load_contacts()
    s = contacts_stats(contacts)
    st.markdown('<div class="section-title">👥 Contatti</div>', unsafe_allow_html=True)

    cols = st.columns(5)
    for col, (val, label, reply) in zip(cols, [
        (s["dm_total"],"DM inviati",False),(s["replied"],"Risposte",True),
        (s["warming"],"In sequenza",False),(s["not_target"],"Non in target",False),(s["total"],"Totale",False)
    ]):
        with col:
            extra = " card-reply" if reply else ""
            st.markdown(f'<div class="card{extra}"><div class="card-value">{val}</div><div class="card-label">{label}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c1,c2,c3 = st.columns([2,2,2])
    with c1: filter_status = st.selectbox("Stato", ["Tutti","Risposta ricevuta","DM inviato","In sequenza","Non in target","Filtrati","Saltati"])
    with c2: search = st.text_input("", placeholder="🔍 Cerca @username", label_visibility="collapsed")
    with c3: sort_by = st.selectbox("Ordina per", ["Più recenti","Più vecchi"])

    stage_map = {"new":"Nuovo","followed":"Seguito","liked_post":"Post likato",
                 "liked_story":"Storia likato","dm_sent":"DM inviato","unfollowed":"Unfollowed",
                 "not_target":"Non in target","filtered":"Filtrato","skipped_private":"Privato"}
    icon_map  = {"dm_sent":"✅","replied":"💬","not_target":"❌","unfollowed":"🔕","filtered":"⏭","skipped_private":"🔒"}

    rows = []
    for username, data in contacts.items():
        status = data.get("status","")
        stage  = data.get("stage","")
        if search and search.lstrip("@").lower() not in username.lower(): continue
        if filter_status == "Risposta ricevuta" and status != "replied": continue
        if filter_status == "DM inviato"        and status != "dm_sent": continue
        if filter_status == "In sequenza"       and stage not in ("new","followed","liked_post","liked_story"): continue
        if filter_status == "Non in target"     and status != "not_target": continue
        if filter_status == "Filtrati"          and status != "filtered": continue
        if filter_status == "Saltati"           and "skip" not in status: continue

        msg = (data.get("message") or data.get("pending_message",""))[:90]
        rows.append({
            "":          icon_map.get(status,"🔄"),
            "Username":  f"@{username}",
            "Stage":     stage_map.get(stage, stage),
            "Stato":     status.replace("dm_sent","DM inviato").replace("not_target","Non in target").replace("skipped_private","Privato").replace("replied","Ha risposto ✅"),
            "Follow-up": str(data.get("followups_done",0)),
            "Messaggio": msg + ("..." if len(msg)==90 else ""),
            "Data":      data.get("timestamp",""),
        })

    if sort_by == "Più vecchi": rows.reverse()

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True, height=520)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Esporta CSV", csv, "contatti_wd.csv", "text/csv")
    else:
        st.markdown('<p style="color:#475569;text-align:center;padding:40px 0">Nessun contatto trovato.</p>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# IMPOSTAZIONI
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Impostazioni":
    st.markdown('<div class="section-title">⚙️ Impostazioni</div>', unsafe_allow_html=True)
    env = load_env()

    tab_acc, tab_filter, tab_msg, tab_sched, tab_notify = st.tabs(["🔐 Account","🎯 Filtri Target","💬 Messaggi","⏰ Orari","🔔 Notifiche"])

    with tab_acc:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">INSTAGRAM</div>', unsafe_allow_html=True)
            username   = st.text_input("Username",   value=env.get("INSTAGRAM_USERNAME",""))
            password   = st.text_input("Password",   value=env.get("INSTAGRAM_PASSWORD",""),   type="password")
            session_id = st.text_input("Session ID", value=env.get("INSTAGRAM_SESSION_ID",""), type="password",
                                       help="Chrome → Ispeziona → Application → Cookies → sessionid")
        with c2:
            st.markdown('<div class="section-header">ANTHROPIC API</div>', unsafe_allow_html=True)
            api_key = st.text_input("API Key", value=env.get("ANTHROPIC_API_KEY",""), type="password")
            st.markdown('<div class="section-header" style="margin-top:20px">LIMITI DM</div>', unsafe_allow_html=True)
            max_dm    = st.number_input("Max DM/giorno",         5,  50, int(env.get("MAX_DM_PER_DAY","15")))
            min_delay = st.number_input("Ritardo minimo (sec)",  20, 300, int(env.get("MIN_DELAY_SECONDS","45")))
            max_delay = st.number_input("Ritardo massimo (sec)", 60, 600, int(env.get("MAX_DELAY_SECONDS","180")))
        if st.button("💾 Salva Account"):
            for k,v in [("INSTAGRAM_USERNAME",username),("INSTAGRAM_PASSWORD",password),
                        ("INSTAGRAM_SESSION_ID",session_id),("ANTHROPIC_API_KEY",api_key),
                        ("MAX_DM_PER_DAY",str(max_dm)),("MIN_DELAY_SECONDS",str(min_delay)),
                        ("MAX_DELAY_SECONDS",str(max_delay))]:
                save_env_key(k,v)
            st.success("✅ Salvato!")

    with tab_filter:
        st.markdown('<p style="color:#8892b0;font-size:0.85rem;margin-bottom:20px">Filtra i profili da contattare. Più i filtri sono precisi, più alta è la qualità dei lead.</p>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">FILTRI PROFILO</div>', unsafe_allow_html=True)
            min_f     = st.number_input("Follower minimi",  0, 10000, int(env.get("MIN_FOLLOWERS","100")))
            max_f     = st.number_input("Follower massimi", 1000, 500000, int(env.get("MAX_FOLLOWERS","50000")))
            min_p     = st.number_input("Post minimi",      0, 50, int(env.get("MIN_POSTS","6")))
            skip_ver  = st.checkbox("Salta account verificati (spunta blu)", value=env.get("SKIP_VERIFIED","true")=="true")
            req_italy = st.checkbox("Solo profili basati in Italia", value=env.get("REQUIRE_ITALY","true")=="true")
        with c2:
            st.markdown('<div class="section-header">PAROLE CHIAVE BIO</div>', unsafe_allow_html=True)
            bio_inc = st.text_input("Includi (virgola tra le parole)", value=env.get("BIO_INCLUDE_KEYWORDS",""),
                                    placeholder="es. imprenditore,lavoro,business")
            bio_exc = st.text_input("Escludi (virgola tra le parole)", value=env.get("BIO_EXCLUDE_KEYWORDS","collaborazioni,brand,sponsor,agenzia"),
                                    placeholder="es. collaborazioni,brand,sponsor")
            st.markdown('<p style="color:#8892b0;font-size:0.78rem;margin-top:8px">Includi: contatta solo chi ha queste parole nella bio. Lascia vuoto per nessun filtro.<br>Escludi: salta chi ha queste parole (influencer, agenzie, ecc).</p>', unsafe_allow_html=True)
        if st.button("💾 Salva Filtri"):
            for k,v in [("MIN_FOLLOWERS",str(min_f)),("MAX_FOLLOWERS",str(max_f)),("MIN_POSTS",str(min_p)),
                        ("SKIP_VERIFIED",str(skip_ver).lower()),("REQUIRE_ITALY",str(req_italy).lower()),
                        ("BIO_INCLUDE_KEYWORDS",bio_inc),("BIO_EXCLUDE_KEYWORDS",bio_exc)]:
                save_env_key(k,v)
            st.success("✅ Filtri salvati!")

    with tab_msg:
        st.markdown('<div class="section-header">TONO DEI MESSAGGI</div>', unsafe_allow_html=True)
        tone_options = {"informale":"😊 Informale — amichevole, come tra pari",
                        "formale":"👔 Formale — professionale, usa 'lei'",
                        "motivazionale":"🔥 Motivazionale — energico, focalizzato sulla crescita"}
        current_tone = env.get("MESSAGE_TONE","informale")
        tone = st.radio("", list(tone_options.values()),
                        index=list(tone_options.keys()).index(current_tone),
                        label_visibility="collapsed")
        tone_key = list(tone_options.keys())[list(tone_options.values()).index(tone)]

        st.markdown('<div class="section-header" style="margin-top:24px">VARIANTI MESSAGGIO (A/B TEST)</div>', unsafe_allow_html=True)
        variants = st.slider("Numero di varianti generate dall'AI per ogni profilo", 1, 3, int(env.get("MESSAGE_VARIANTS","2")),
                             help="L'AI genera più versioni e ne sceglie una a caso — maggiore varietà = minore rischio ban")

        if st.button("💾 Salva Messaggi"):
            save_env_key("MESSAGE_TONE", tone_key)
            save_env_key("MESSAGE_VARIANTS", str(variants))
            st.success("✅ Salvato!")

    with tab_sched:
        st.markdown('<div class="section-header">FASCIA ORARIA</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1: start_h = st.number_input("Ora inizio", 0, 12, int(env.get("ACTIVE_HOURS_START","9")))
        with c2: end_h   = st.number_input("Ora fine",   14, 23, int(env.get("ACTIVE_HOURS_END","21")))

        st.markdown('<div class="section-header" style="margin-top:20px">GIORNI ATTIVI</div>', unsafe_allow_html=True)
        day_names = {1:"Lunedì",2:"Martedì",3:"Mercoledì",4:"Giovedì",5:"Venerdì",6:"Sabato",7:"Domenica"}
        current_days = [int(d) for d in env.get("ACTIVE_DAYS","1,2,3,4,5,6,7").split(",") if d.strip()]
        selected_days = []
        cols_days = st.columns(7)
        for i, (num, name) in enumerate(day_names.items()):
            with cols_days[i]:
                if st.checkbox(name[:3], value=num in current_days, key=f"day_{num}"):
                    selected_days.append(num)

        if st.button("💾 Salva Orari"):
            save_env_key("ACTIVE_HOURS_START", str(start_h))
            save_env_key("ACTIVE_HOURS_END", str(end_h))
            save_env_key("ACTIVE_DAYS", ",".join(map(str, selected_days or [1,2,3,4,5,6,7])))
            st.success("✅ Salvato!")

    with tab_notify:
        st.markdown('<div class="section-header">NOTIFICHE RISPOSTA</div>', unsafe_allow_html=True)
        st.markdown('<p style="color:#8892b0;font-size:0.85rem;margin-bottom:16px">Ricevi una notifica quando qualcuno risponde al DM. Usa un webhook di Make.com o Zapier per riceverla su WhatsApp o email.</p>', unsafe_allow_html=True)
        notify_on = st.checkbox("Attiva notifiche risposta", value=env.get("NOTIFY_ON_REPLY","false")=="true")
        webhook   = st.text_input("Webhook URL (Make / Zapier)", value=env.get("NOTIFY_WEBHOOK",""),
                                  placeholder="https://hook.make.com/...", disabled=not notify_on)
        if st.button("💾 Salva Notifiche"):
            save_env_key("NOTIFY_ON_REPLY", str(notify_on).lower())
            save_env_key("NOTIFY_WEBHOOK", webhook)
            st.success("✅ Salvato!")

    st.markdown("---")
    st.markdown('<div style="font-weight:600;color:#f87171;margin-bottom:12px;font-size:0.82rem">ZONA PERICOLOSA</div>', unsafe_allow_html=True)
    if st.button("🗑️  Azzera lista contatti"):
        CONTACTS_FILE.write_text("{}", encoding="utf-8"); st.success("Lista azzerata."); st.rerun()
