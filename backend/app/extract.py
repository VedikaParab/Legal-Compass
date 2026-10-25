"""Rule-based fact extraction from a free-text narrative.

Pulls out what the rest of the pipeline needs most: the offence date (for the temporal rule), the state,
amounts, and hints that pre-answer follow-up questions (weapon used, online, police status, injury...).
An optional LLM (see llm.py) can add to these facts, but the app works fully without one.
"""
from __future__ import annotations

import re
from datetime import date

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MON = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"

DATE_PATTERNS = [
    # 12 March 2024, 12th of March, 2024
    (re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?{MON}\.?,?\s+(\d{{4}})\b", re.I), ("d", "m", "y")),
    # March 12, 2024
    (re.compile(rf"\b{MON}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I), ("m", "d", "y")),
    # 2024-03-12
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), ("y", "m", "d")),
    # 12/03/2024 or 12-03-2024 or 12.03.2024 (Indian day-first order)
    (re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b"), ("d", "m", "y")),
]
MONTH_YEAR = re.compile(rf"\b(?:in\s+)?{MON}\.?,?\s+(\d{{4}})\b", re.I)

STATES = ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
          "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
          "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
          "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir", "Ladakh",
          "Puducherry", "Chandigarh", "Andaman and Nicobar Islands", "Dadra and Nagar Haveli and Daman and Diu",
          "Lakshadweep"]
CITIES = {"mumbai": "Maharashtra", "pune": "Maharashtra", "thane": "Maharashtra", "navi mumbai": "Maharashtra",
          "nagpur": "Maharashtra", "nashik": "Maharashtra", "bengaluru": "Karnataka", "bangalore": "Karnataka",
          "chennai": "Tamil Nadu", "hyderabad": "Telangana", "kolkata": "West Bengal", "new delhi": "Delhi",
          "noida": "Uttar Pradesh", "lucknow": "Uttar Pradesh", "gurgaon": "Haryana", "gurugram": "Haryana",
          "ahmedabad": "Gujarat", "surat": "Gujarat", "jaipur": "Rajasthan", "bhopal": "Madhya Pradesh",
          "indore": "Madhya Pradesh", "patna": "Bihar", "kochi": "Kerala", "thiruvananthapuram": "Kerala",
          "chandigarh": "Chandigarh", "bhubaneswar": "Odisha", "guwahati": "Assam", "ranchi": "Jharkhand"}

AMOUNT = re.compile(r"(?:rs\.?|inr|₹|rupees)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores|k)?"
                    r"|([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)\b"
                    r"|([\d,]{3,}(?:\.\d+)?)\s*(?:/-\s*)?(?:rupees|rs\b|inr\b)", re.I)

HINTS = {
    "weapon": (r"\b(knife|gun|pistol|revolver|rod|iron rod|stick|lathi|sword|acid|blade|axe|bat|sickle|weapon|stabbed|shot)\b", "Yes"),
    "online": (r"\b(online|upi|otp|whatsapp|instagram|facebook|telegram|website|app|link|phone call|video call|email|kyc|paytm|gpay|phonepe|net ?banking|credit card|debit card)\b", "Yes"),
    "night": (r"\b(at night|midnight|late night|night time|\d{1,2}\s*(?:am)\b|in the night)\b", "Yes"),
}
POLICE = [
    (r"\bfirst information report\b|\bF\.?I\.?R\.? (no|number)\.?\s*[:\-]?\s*\d", "Yes, FIR registered"),
    (r"\b(police|they|sho|officer)\b.{0,40}\b(refused|did not|didn't|won't|would not)\b.{0,30}\b(fir|register|complaint)\b", "Yes, but police refused to register an FIR"),
    (r"\b(fir (was |has been )?(registered|filed|lodged)|filed an? fir|lodged an? fir|registered an? fir)\b", "Yes, FIR registered"),
]
INJURY = [
    (r"\b(fracture\w*|broke (my|his|her|their) (\w+ )?(arm|leg|hand|bone|nose|jaw|ribs?|teeth|skull|finger)s?|broken (arm|leg|hand|bone|nose|jaw|ribs?|teeth)|hospitali[sz]ed|admitted|stitches|deep wound|icu|unconscious|bleeding heavily|lost (his|her|my) (eye|tooth|teeth))\b",
     "Serious injury (fracture, deep wound, hospitalisation)"),
    (r"\b(bruise\w*|minor (cut|injur\w*)|swelling|scratch\w*|slapped)\b", "Simple injury (bruises, minor cuts)"),
]
RELATION = [
    (r"\b(husband|in-?laws|mother-in-law|father-in-law|sister-in-law|brother-in-law|sasural|saas|sasur|pati)\b", "Husband / in-laws"),
    (r"\b(brother|sister|father|mother|uncle|aunt|cousin|son|daughter)\b", "Family member"),
    (r"\b(colleague|neighbou?r|friend|landlord|tenant|employer|boss|classmate)\b", "Acquaintance / colleague"),
    (r"\b(stranger|unknown (man|men|person|people|caller|number))\b", "Stranger"),
]
DEATH = r"\b(died|dead|death|killed|murdered|passed away)\b"
GROUP = [(r"\b(five|six|seven|eight|ten|\d{2}|several|many|a group of|mob|gang)\b.{0,20}\b(men|people|persons|boys|accused|of them)\b", "Five or more people"),
         (r"\b(two|three|four|2|3|4)\b.{0,15}\b(men|people|persons|boys|accused|of them)\b|\b(he and his|she and her|along with (his|her))\b", "Two to four people")]


def _mk(y, m, d):
    try:
        return date(int(y), int(m), int(d))
    except ValueError:
        return None


def find_dates(text: str) -> list[date]:
    out = []
    for rx, order in DATE_PATTERNS:
        for m in rx.finditer(text):
            parts = dict(zip(order, m.groups()))
            mo = parts["m"]
            mo = MONTHS[mo[:3].lower()] if not str(mo).isdigit() else int(mo)
            d = _mk(parts["y"], mo, parts["d"])
            if d and 1950 <= d.year <= date.today().year + 1:
                out.append(d)
    return sorted(set(out))


def find_amount(text: str) -> str | None:
    m = AMOUNT.search(text)
    if not m:
        return None
    num = (m.group(1) or m.group(3) or m.group(5) or "").replace(",", "")
    unit = (m.group(2) or m.group(4) or "").lower()
    try:
        v = float(num)
    except ValueError:
        return None
    v *= {"lakh": 1e5, "lakhs": 1e5, "crore": 1e7, "crores": 1e7, "k": 1e3}.get(unit, 1)
    return f"₹{v:,.0f}"


def find_state(text: str) -> str | None:
    low = text.lower()
    for s in STATES:
        if s.lower() in low:
            return s
    for c, s in CITIES.items():
        if re.search(rf"\b{re.escape(c)}\b", low):
            return s
    return None


def extract(text: str) -> dict:
    """Facts plus pre-filled answers (marked as inferred, so the UI can let the user correct them)."""
    from . import devanagari
    facts: dict = {}
    inferred: dict = {}
    dev = devanagari.has_devanagari(text)
    if dev:
        facts["script"] = "devanagari"
        inferred.update(devanagari.infer(text))
        text = devanagari.normalize(text)
    dates = find_dates(text)
    if dates:
        facts["dates_mentioned"] = [d.isoformat() for d in dates]
        inferred["offence_date"] = dates[0].isoformat()  # earliest date = most likely the incident
        if len(dates) > 1 and dates[0] < date(2024, 7, 1) <= dates[-1]:
            facts["date_note"] = "Several dates mentioned on both sides of 1 July 2024 - please confirm the incident date."
    else:
        my = MONTH_YEAR.search(text)
        if my:
            facts["approximate_month"] = f"{my.group(1).title()} {my.group(2)}"
    st = find_state(text)
    if st:
        inferred["state"] = st
    amt = find_amount(text)
    if amt:
        inferred["amount"] = amt
    for qid, (rx, val) in HINTS.items():
        if re.search(rx, text, re.I):
            inferred.setdefault(qid, val)
    for rx, val in POLICE:
        if re.search(rx, text, re.I):
            inferred["police_status"] = val
            break
    for rx, val in INJURY:
        if re.search(rx, text, re.I):
            inferred["injury"] = val
            break
    for rx, val in RELATION:
        if re.search(rx, text, re.I):
            inferred["relationship"] = val
            break
    for rx, val in GROUP:
        if re.search(rx, text, re.I):
            inferred["accused_count"] = val
            break
    if re.search(r"\b(from|in|inside|into) (my|our|the|her|his) (house|home|flat|room|apartment|bedroom|shop|office|godown)\b", text, re.I):
        inferred["property_place"] = "From inside a house or building"
    elif re.search(r"\b(from|in) (my|her|his) (bag|pocket|purse|car|vehicle|bike)\b|\bpickpocket", text, re.I):
        inferred["property_place"] = "From my person / bag / vehicle"
    if re.search(DEATH, text, re.I):
        inferred["death"] = "Yes"
    if re.search(r"\b(again and again|repeatedly|for (the last|past) \w+ (months|years)|since \d{4}|continuously|every day|daily)\b", text, re.I):
        inferred["ongoing"] = "Over a period (still continuing or repeated)"
    if dev and (ms := devanagari.SINCE.search(text)) and int(ms.group(1)) <= date.today().year:
        inferred["ongoing"] = "Over a period (still continuing or repeated)"
        facts["ongoing_since_year"] = int(ms.group(1))
    m = re.search(r"\b(?:since|from|starting in|beginning in)\s+(?:(?:early|mid|late)\s+)?(?:" + MON + r"\.?,?\s+)?((?:19|20)\d{2})\b", text, re.I)
    if m and int(m.group(m.lastindex)) <= date.today().year:
        inferred["ongoing"] = "Over a period (still continuing or repeated)"
        facts["ongoing_since_year"] = int(m.group(m.lastindex))
    facts["word_count"] = len(text.split())
    return {"facts": facts, "inferred": inferred}
