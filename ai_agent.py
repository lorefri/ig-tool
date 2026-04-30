import json
import random
import anthropic
from config import (
    ANTHROPIC_API_KEY, COMPANY_CONTEXT, MESSAGE_TONE, MESSAGE_VARIANTS,
    REQUIRE_ITALY, OBJECTIVE, OBJECTIVE_CUSTOM, OBJECTIVE_CONTEXTS
)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

TONE_DESCRIPTIONS = {
    "informale":     "amichevole, diretto, come tra pari. Usa 'tu', tono leggero.",
    "formale":       "professionale e rispettoso. Usa 'lei', tono curato.",
    "motivazionale": "energico, ispirazionale, focalizzato sulla crescita e il cambiamento.",
}


def _get_objective_context() -> str:
    if OBJECTIVE == "custom":
        return f"\nOBIETTIVO PERSONALIZZATO: {OBJECTIVE_CUSTOM}\n" if OBJECTIVE_CUSTOM else ""
    return OBJECTIVE_CONTEXTS.get(OBJECTIVE, OBJECTIVE_CONTEXTS["entrambi"])


def analyze_profile(username, full_name, bio, followers, following, posts, location="") -> dict:
    tone_desc   = TONE_DESCRIPTIONS.get(MESSAGE_TONE, TONE_DESCRIPTIONS["informale"])
    obj_context = _get_objective_context()
    italy_note  = "IMPORTANTE: Il profilo deve sembrare basato in Italia. Se non ci sono indizi (città, regioni, cultura italiana), metti in_italy: false." if REQUIRE_ITALY else ""
    n_variants  = max(1, MESSAGE_VARIANTS)

    profile_info = f"""Username: @{username}
Nome: {full_name or 'non disponibile'}
Bio: {bio or 'nessuna bio'}
Follower: {followers} | Seguiti: {following} | Post: {posts}
Posizione dichiarata: {location or 'non specificata'}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=f"""Sei un assistente per WD International University.
{COMPANY_CONTEXT}
{obj_context}
{italy_note}

Analizza il profilo Instagram e decidi se è in target per l'obiettivo indicato.

Rispondi SOLO con questo JSON (nessun testo fuori):
{{
  "in_target": true/false,
  "in_italy": true/false,
  "motivo": "spiegazione max 15 parole",
  "messaggi": ["variante 1", "variante 2"]
}}

Regole per i messaggi (genera esattamente {n_variants} varianti):

STRUTTURA OBBLIGATORIA — 3 righe max:
1. Apertura specifica: osservazione concreta su qualcosa del loro profilo (settore, lavoro, bio, niche). MAI frasi generiche come "spero che tutto vada bene" o "ho visto il tuo profilo".
2. Aggancio naturale: una frase che spiega perché li contatti proprio loro, senza rivelare nulla di quello che proponi.
3. Domanda finale: una domanda su di LORO — la loro situazione attuale, i loro obiettivi, se stanno ancora portando avanti qualcosa. Deve essere una domanda a cui si risponde facilmente con 2-3 parole.

VIETATO ASSOLUTAMENTE nel primo messaggio:
- Qualsiasi menzione di call, appuntamento, videochimata, parlarne, incontrarsi
- Parole come: opportunità, idea, proposta, collaborazione, guadagno, reddito, business, corsi, formazione, azienda
- Frasi come "vorrei condividere con te", "ho qualcosa che potrebbe interessarti", "posso parlartene"
- Emoji in eccesso — max 1, e solo se aggiunge qualcosa
- Tono commerciale o da venditore

OBIETTIVO del primo messaggio: ottenere una risposta, non vendere nulla.
Il messaggio deve sembrare scritto da una persona reale che ha guardato davvero il loro profilo.

Esempi di struttura corretta (NON copiarli, usali solo come riferimento di tono):
- "Ciao [nome], ho visto che ti occupi di [cosa fa] — è ancora il tuo focus principale o stai prendendo direzioni diverse?"
- "Ciao [nome], seguo il lavoro di chi opera nel [loro settore] — stai ancora sviluppando questo percorso attivamente?"
- "Ciao [nome], [osservazione specifica sul loro contenuto/bio]. Hai ancora voglia di crescere in questo ambito?"

Tono: {tone_desc}
Ogni variante deve avere una domanda finale diversa ma sempre su di loro.
Se in_target è false → "messaggi": []
""",
        messages=[{"role": "user", "content": f"Profilo da analizzare:\n{profile_info}"}]
    )

    text = response.content[0].text.strip()
    start, end = text.find("{"), text.rfind("}") + 1
    result = json.loads(text[start:end])

    messaggi = result.get("messaggi", [])
    result["messaggio"] = random.choice(messaggi) if messaggi else ""

    if REQUIRE_ITALY and not result.get("in_italy", True):
        result["in_target"] = False
        result["motivo"] = "Profilo non in Italia"

    return result


def generate_followup(username: str, full_name: str, original_message: str, attempt: int) -> str:
    tone_desc   = TONE_DESCRIPTIONS.get(MESSAGE_TONE, TONE_DESCRIPTIONS["informale"])
    obj_context = _get_objective_context()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=f"""Sei un assistente per WD International University.
{COMPANY_CONTEXT}
{obj_context}
Scrivi un follow-up DM su Instagram. Tono: {tone_desc}.

Il primo messaggio non ha ricevuto risposta. Il follow-up deve:
- Essere max 2 righe
- NON ripetere o parafrasare il primo messaggio
- NON chiedere di fissare una call o un appuntamento
- NON sembrare disperato o insistente
- Aggiungere un elemento nuovo: una domanda diversa su di loro, un accenno molto vago a qualcosa che stai sviluppando (senza specificare cosa), oppure un aggancio su un loro contenuto recente
- Chiudere sempre con una domanda semplice su di loro

Scrivi SOLO il testo del messaggio, niente altro.""",
        messages=[{"role": "user", "content": f"Utente: @{username} ({full_name})\nPrimo messaggio: {original_message}\nFollow-up numero {attempt}."}]
    )
    return response.content[0].text.strip()
