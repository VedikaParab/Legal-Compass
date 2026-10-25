"""Offence catalogue used by the rule-based predictor and the question engine.

Each offence lists
  * patterns  - regular expressions over the user's narrative (English + common Hinglish words)
  * ipc       - the IPC section(s) it usually attracts; BNS counterparts are NOT written here, they are
                looked up live in the LegalCompass mapping so the app and the dataset never disagree
  * refine    - answer-dependent replacements (e.g. hurt with a weapon -> IPC 324 instead of 323)
  * questions - follow-up questions that matter for this offence

This is a navigation aid, not legal advice: the output is always "possibly applicable sections".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Question:
    id: str
    text: str
    kind: str = "choice"          # choice | date | text
    options: list[str] = field(default_factory=list)
    why: str = ""
    required: bool = False


@dataclass
class Offence:
    id: str
    label: str
    patterns: list[str]
    ipc: list[str]
    category: str
    questions: list[str] = field(default_factory=list)
    refine: dict = field(default_factory=dict)      # {question_id: {answer: [ipc sections]}}
    serious: bool = False


# ------------------------------------------------------------------ questions
QUESTIONS: dict[str, Question] = {q.id: q for q in [
    Question("offence_date", "When did the incident happen?", "date",
             why="The date decides whether the old codes (IPC) or the new codes (BNS) apply. "
                 "Offences before 1 July 2024 stay under the IPC.", required=True),
    Question("fir_date", "When was the FIR registered?", "date",
             why="Proceedings that began before 1 July 2024 continue under the CrPC; later ones follow the BNSS."),
    Question("ongoing", "Did it happen once, or has it continued over a period of time?", "choice",
             ["Once", "Over a period (still continuing or repeated)"],
             why="A continuing offence that spans 1 July 2024 may fall under both codes."),
    Question("state", "In which state or union territory did it happen?", "text",
             why="Used for jurisdiction, helplines and finding similar cases."),
    Question("police_status", "Have you approached the police yet?", "choice",
             ["Not yet", "Yes, FIR registered", "Yes, but police refused to register an FIR"],
             why="Changes the next steps we suggest."),
    Question("accused_count", "How many people were involved in committing it?", "choice",
             ["One person", "Two to four people", "Five or more people"],
             why="Acts done together can add common-intention or group provisions."),
    Question("injury", "How serious was the injury?", "choice",
             ["No visible injury", "Simple injury (bruises, minor cuts)", "Serious injury (fracture, deep wound, hospitalisation)"],
             why="Simple and grievous hurt are different offences."),
    Question("weapon", "Was any weapon or dangerous object used?", "choice", ["No", "Yes"],
             why="Hurt caused with a dangerous weapon is a more serious offence."),
    Question("property_place", "Where was the property taken from?", "choice",
             ["From my person / bag / vehicle", "From inside a house or building", "Elsewhere"],
             why="Theft from a dwelling house is a separate, more serious offence."),
    Question("force_used", "Was force or threat used while taking the property?", "choice", ["No", "Yes"],
             why="Theft with force or threat can amount to robbery or extortion."),
    Question("online", "Did it happen online or over phone / UPI / social media?", "choice", ["No", "Yes"],
             why="Online fraud also attracts the Information Technology Act and has a dedicated helpline."),
    Question("amount", "Approximately how much money or property value was involved?", "text",
             why="Helps describe the loss in a complaint."),
    Question("relationship", "What is your relationship with the accused?", "choice",
             ["Husband / in-laws", "Family member", "Acquaintance / colleague", "Stranger"],
             why="Cruelty by a husband or his relatives is a specific offence."),
    Question("night", "Did the break-in happen at night?", "choice", ["No", "Yes"],
             why="House-breaking by night is treated more seriously."),
    Question("death", "Did anyone die as a result?", "choice", ["No", "Yes"],
             why="Determines whether homicide provisions apply."),
]}

# ------------------------------------------------------------------ offences
OFFENCES: list[Offence] = [
    Offence("murder", "Murder / killing", [r"\bmurder(ed)?\b", r"\bkill(ed|ing)\b", r"\bkilled\b", r"\bhatya\b", r"\bstabbed .* (died|dead)\b", r"\bbeaten to death\b"],
            ["302"], "body", ["death", "weapon", "accused_count"], serious=True),
    Offence("attempt_murder", "Attempt to murder", [r"\battempt(ed)? to (murder|kill)\b", r"\btried to kill\b", r"\bwanted to kill\b"],
            ["307"], "body", ["injury", "weapon", "accused_count"], serious=True),
    Offence("negligent_death", "Death by negligence / accident", [r"\b(accident|negligen\w+|hit[- ]and[- ]run)\b.*\b(died|death|dead)\b", r"\b(died|death)\b.*\b(accident|negligen\w+)\b"],
            ["304A"], "body", ["death"], serious=True),
    Offence("rash_driving", "Rash or negligent driving", [r"\brash(ly)? driv\w*", r"\bover ?speed\w*", r"\bdrunk driv\w*", r"\b(car|bike|truck|bus|auto)\b.*\b(hit|rammed|knocked)\b"],
            ["279"], "body", ["injury"],
            refine={"injury": {"Simple injury (bruises, minor cuts)": ["279", "337"],
                               "Serious injury (fracture, deep wound, hospitalisation)": ["279", "338"]}}),
    Offence("hurt", "Assault / causing hurt", [r"\b(beat|beaten|hit|slapped|punched|kicked|assault\w*|attacked|thrashed)\b", r"\bmaar(a|pit|peet)\b", r"\binjur\w+\b"],
            ["323"], "body", ["injury", "weapon", "accused_count"],
            refine={"injury": {"Serious injury (fracture, deep wound, hospitalisation)": ["325"]},
                    "weapon": {"Yes": ["324"]},
                    "_combo": {("Serious injury (fracture, deep wound, hospitalisation)", "Yes"): ["326"]}}),
    Offence("restraint", "Wrongful restraint / confinement", [r"\b(locked (me|her|him) (up|in)|confined|not allowed to leave|held (me|her|him) captive|blocked (my|her|his) way|wrongful(ly)? restrain\w*)\b"],
            ["341"], "body", [], refine={}),
    Offence("kidnapping", "Kidnapping / abduction", [r"\bkidnap\w*", r"\babduct\w*", r"\b(taken|took) away (my|our) (son|daughter|child)\b", r"\bmissing child\b"],
            ["363"], "body", ["accused_count"], serious=True),
    Offence("rape", "Rape / sexual assault", [r"\brape[ds]?\b", r"\bsexual(ly)? assault\w*", r"\bforced (me|her) (into|to have) (sex|physical relations)\b", r"\bbalatkar\b"],
            ["376"], "women", ["accused_count"], serious=True),
    Offence("molestation", "Molestation / outraging modesty", [r"\bmolest\w*", r"\b(touched|groped|grabbed) (me|her)\b", r"\boutrag\w* (her|my) modesty\b", r"\bchhed\w*\b"],
            ["354"], "women", []),
    Offence("sexual_harassment", "Sexual harassment", [r"\bsexual(ly)? harass\w*", r"\b(sexual|obscene|vulgar) (remarks|comments|messages|demands)\b", r"\bshowed (me|her) porn\w*"],
            ["354A"], "women", ["online"]),
    Offence("stalking", "Stalking", [r"\bstalk\w*", r"\bfollow(s|ed|ing) (me|her) (everywhere|daily|repeatedly|home)\b", r"\bkeeps? (messaging|calling) (me|her) despite\b"],
            ["354D"], "women", ["online"]),
    Offence("voyeurism", "Voyeurism / secret recording", [r"\b(secretly|hidden camera).*(record|film|photo)\w*", r"\bvoyeur\w*", r"\b(record|film)\w* (me|her) (changing|bathing)\b"],
            ["354C"], "women", ["online"]),
    Offence("insult_woman", "Insulting the modesty of a woman", [r"\b(lewd|obscene) (gesture|words|remarks)\b", r"\beve[- ]teas\w*"],
            ["509"], "women", []),
    Offence("cruelty", "Cruelty by husband or in-laws", [r"\b(husband|in-?laws|mother-in-law|father-in-law|sasural|sasur|saas)\b.*\b(harass\w*|torture\w*|beat\w*|cruel\w*|dowry|abuse\w*)\b",
                                                           r"\bdowry\b", r"\bdahej\b", r"\bdomestic violence\b"],
            ["498A"], "women", ["relationship", "injury"], refine={}),
    Offence("dowry_death", "Dowry death", [r"\bdowry\b.*\b(died|death|dead|burnt|suicide)\b", r"\b(died|death|burnt)\b.*\bdowry\b"],
            ["304B", "498A"], "women", ["relationship"], serious=True),
    Offence("abetment_suicide", "Abetment of suicide", [r"\b(abet\w*|drove|forced|pushed) .*\bsuicide\b", r"\bsuicide note\b", r"\bcommitted suicide because\b"],
            ["306"], "body", [], serious=True),
    Offence("theft", "Theft", [r"\b(stole|stolen|theft|thief|steal\w*|pickpocket\w*|chor[iy]?|went missing from)\b", r"\bsnatch\w*",
                               r"\b(took|taken|carried|ran away with|made off with) (away )?(my|our|her|his) (\w+ ){0,2}(phone|mobile|wallet|purse|chain|jewel\w*|money|cash|bike|scooter|car|laptop|bag|gold|ornaments?|valuables)\b"],
            ["379"], "property", ["property_place", "force_used", "amount", "night"],
            refine={"property_place": {"From inside a house or building": ["380"]},
                    "force_used": {"Yes": ["392"]}}),
    Offence("housebreaking", "House-breaking / burglary", [r"\bbroke (into|in)\b", r"\bbreak[- ]?in\b", r"\bburglar\w*", r"\b(lock|door|window) (was )?broken\b"],
            ["454", "380"], "property", ["night", "amount"],
            refine={"night": {"Yes": ["457", "380"]}}),
    Offence("trespass", "Trespass", [r"\btrespass\w*", r"\b(entered|barged into) (my|our) (house|home|property|land|shop)\b", r"\bencroach\w*"],
            ["447"], "property", [], refine={}),
    Offence("robbery", "Robbery", [r"\brobb(ed|ery)\b", r"\bat (knife|gun)[- ]?point\b", r"\blooted\b"],
            ["392"], "property", ["accused_count", "weapon", "amount"],
            refine={"accused_count": {"Five or more people": ["395"]}}, serious=True),
    Offence("extortion", "Extortion", [r"\bextort\w*", r"\bdemand(ed|ing)? (money|ransom|protection money)\b.*\bthreat\w*", r"\bthreat\w*.*\b(pay|money)\b", r"\bblackmail\w*", r"\bhafta\b"],
            ["384"], "property", ["online", "amount"]),
    Offence("cheating", "Cheating / fraud", [r"\bcheat\w*", r"\bfraud\w*", r"\bscam\w*", r"\bduped\b", r"\bdhokha\b", r"\bponzi\b", r"\bfake (job|offer|loan|investment|website|call)\b",
                                             r"\b(otp|upi|kyc)\b.*\b(fraud|cheat|debited|lost|transferred)\b", r"\bmoney (was )?(debited|deducted)\b",
                                             r"\b(otp|cvv|upi pin|atm pin)\b", r"\b(lost|debited|transferred)\b[^.]{0,30}(rs\.?|₹|rupees)\s*[\d,]+[^.]{0,30}\b(upi|online|link|app|account)\b"],
            ["420"], "property", ["online", "amount"], refine={}),
    Offence("impersonation", "Cheating by impersonation", [r"\bpretend\w* to be\b", r"\bposed as\b", r"\bimpersonat\w*", r"\bfake (profile|account|id|police|officer)\b"],
            ["419"], "property", ["online"]),
    Offence("breach_of_trust", "Criminal breach of trust / misappropriation", [r"\bbreach of trust\b", r"\bmisappropriat\w*", r"\bembezzl\w*", r"\b(entrusted|gave him|gave her).*\b(refus\w*|not return\w*|did not return|kept)\b"],
            ["406"], "property", ["amount"]),
    Offence("stolen_property", "Receiving stolen property", [r"\b(bought|received|found with) stolen\b"], ["411"], "property", []),
    Offence("forgery", "Forgery / fake documents", [r"\bforg(ed|ery)\b", r"\bfake (document|signature|certificate|stamp|deed|will)\b", r"\bfabricat\w* (document|record)\b"],
            ["465", "471"], "property", ["online"], refine={}),
    Offence("mischief", "Damage to property (mischief)", [r"\b(damaged|vandali[sz]ed|smashed|broke) (my|our) (car|vehicle|window|shop|property|house|bike)\b", r"\bset (fire|on fire) to\b"],
            ["427"], "property", ["amount"]),
    Offence("intimidation", "Criminal intimidation / threats", [r"\bthreat\w*", r"\bintimidat\w*", r"\bdhamki\b", r"\bsaid (he|she|they) would kill\b"],
            ["506"], "public", ["online", "weapon"]),
    Offence("defamation", "Defamation", [r"\bdefam\w*", r"\b(spread|posted) (false|fake) (rumou?rs|news|allegations)\b", r"\bdamag\w* (my|our) reputation\b"],
            ["500"], "public", ["online"]),
    Offence("insult_peace", "Insult to provoke breach of peace", [r"\b(abused|abusive language|gali|gaali|insulted) (me|us)\b", r"\bfilthy language\b"],
            ["504"], "public", []),
    Offence("rioting", "Rioting / mob violence", [r"\briot\w*", r"\bmob\b", r"\bgroup of (people|men) attacked\b", r"\blynch\w*"],
            ["147"], "public", ["weapon", "injury"], refine={"weapon": {"Yes": ["148"]}}, serious=True),
]

BY_ID = {o.id: o for o in OFFENCES}

# offences that subsume a weaker match (avoid listing both)
SUBSUMES = {
    "murder": {"hurt", "attempt_murder", "intimidation"},
    "attempt_murder": {"hurt", "intimidation"},
    "robbery": {"theft", "hurt", "extortion", "intimidation"},
    "housebreaking": {"theft", "trespass"},
    "dowry_death": {"cruelty"},
    "rape": {"molestation", "hurt"},
    "extortion": {"intimidation"},
    "impersonation": set(),
    "negligent_death": {"rash_driving"},
}

_COMPILED = [(o, [re.compile(p, re.I) for p in o.patterns]) for o in OFFENCES]


def match_offences(text: str) -> list[dict]:
    """Return matched offences with the phrases that triggered them (English, Hinglish, Hindi, Marathi)."""
    from .devanagari import has_devanagari, match as dev_match
    dev = dev_match(text) if has_devanagari(text) else {}
    hits = []
    for o, pats in _COMPILED:
        ev = []
        for p in pats:
            m = p.search(text)
            if m:
                ev.append(m.group(0)[:80])
        ev += dev.get(o.id, [])
        if ev:
            hits.append({"id": o.id, "evidence": ev, "score": min(1.0, 0.55 + 0.15 * len(ev))})
    ids = {h["id"] for h in hits}
    drop = set()
    for h in ids:
        drop |= SUBSUMES.get(h, set()) & ids
    return [h for h in hits if h["id"] not in drop]


def sections_for(offence_id: str, answers: dict) -> list[str]:
    """IPC sections for an offence after applying answer-dependent refinements."""
    o = BY_ID[offence_id]
    secs = list(o.ipc)
    combo = o.refine.get("_combo", {})
    key = tuple(answers.get(q) for q in ("injury", "weapon"))
    if key in combo:
        return list(combo[key])
    for qid, table in o.refine.items():
        if qid.startswith("_"):
            continue
        a = answers.get(qid)
        if a in table:
            secs = list(table[a])
    return secs
