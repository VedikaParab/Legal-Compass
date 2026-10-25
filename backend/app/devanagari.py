"""Hindi and Marathi (Devanagari) understanding for the rule engine.

Devanagari vowel signs are combining marks, so `\\b` word boundaries do not work reliably; these patterns
are plain substrings. Common transliterated (Hinglish) words are already in offences.py.
"""
from __future__ import annotations

import re

DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
MONTHS = {  # Hindi and Marathi month names -> English, so the existing date parser understands them
    "जनवरी": "January", "जानेवारी": "January", "फ़रवरी": "February", "फरवरी": "February", "फेब्रुवारी": "February",
    "मार्च": "March", "अप्रैल": "April", "एप्रिल": "April", "मई": "May", "मे ": "May ", "जून": "June",
    "जुलाई": "July", "जुलै": "July", "अगस्त": "August", "ऑगस्ट": "August", "सितंबर": "September", "सितम्बर": "September",
    "सप्टेंबर": "September", "अक्टूबर": "October", "अक्तूबर": "October", "ऑक्टोबर": "October", "नवंबर": "November",
    "नवम्बर": "November", "नोव्हेंबर": "November", "दिसंबर": "December", "दिसम्बर": "December", "डिसेंबर": "December",
}
PLACES = {"महाराष्ट्र": "Maharashtra", "मुंबई": "Maharashtra", "पुणे": "Maharashtra", "ठाणे": "Maharashtra", "नागपूर": "Maharashtra",
          "नाशिक": "Maharashtra", "दिल्ली": "Delhi", "उत्तर प्रदेश": "Uttar Pradesh", "लखनऊ": "Uttar Pradesh", "बिहार": "Bihar",
          "पटना": "Bihar", "राजस्थान": "Rajasthan", "जयपुर": "Rajasthan", "मध्य प्रदेश": "Madhya Pradesh", "भोपाल": "Madhya Pradesh",
          "इंदौर": "Madhya Pradesh", "गुजरात": "Gujarat", "अहमदाबाद": "Gujarat", "हरियाणा": "Haryana", "गुरुग्राम": "Haryana",
          "पंजाब": "Punjab", "झारखंड": "Jharkhand", "छत्तीसगढ़": "Chhattisgarh", "उत्तराखंड": "Uttarakhand", "गोवा": "Goa",
          "कर्नाटक": "Karnataka", "बेंगलुरु": "Karnataka",
          # Marathi locative forms ("in Pune", "in Mumbai" ...)
          "पुण्यात": "Maharashtra", "मुंबईत": "Maharashtra", "ठाण्यात": "Maharashtra", "नागपुरात": "Maharashtra",
          "नाशिकमध्ये": "Maharashtra", "दिल्लीत": "Delhi", "दिल्ली में": "Delhi", "मुंबई में": "Maharashtra"}

OFFENCE_WORDS = {
    "murder": ["हत्या", "मार डाला", "मार डाली", "जान से मार दिया", "खून केला", "ठार मारले"],
    "attempt_murder": ["जान से मारने की कोशिश", "हत्या का प्रयास", "मारण्याचा प्रयत्न", "खुनाचा प्रयत्न"],
    "hurt": ["मारपीट", "मारा", "पीटा", "पिटाई", "थप्पड़", "चोट पहुँचा", "मारहाण", "मारले", "जखमी", "घायल"],
    "kidnapping": ["अपहरण", "उठा ले गए", "पळवून नेले"],
    "rape": ["बलात्कार", "दुष्कर्म", "लैंगिक अत्याचार"],
    "molestation": ["छेड़छाड़", "छेड़खानी", "गलत तरीके से छुआ", "विनयभंग"],
    "sexual_harassment": ["यौन उत्पीड़न", "अश्लील", "लैंगिक छळ"],
    "stalking": ["पीछा करता", "पीछा करते", "पाठलाग"],
    "cruelty": ["दहेज", "ससुराल", "हुंडा", "हुंड्या", "छळ", "सासरच्या", "सासरी", "घरेलू हिंसा", "कौटुंबिक हिंसा"],
    "theft": ["चोरी", "चुरा", "चोरले", "चोरली", "चोरला", "चोरीला", "छीन", "हिसकावून"],
    "housebreaking": ["सेंध", "ताला तोड़", "घरफोडी", "कुलूप तोडून"],
    "robbery": ["लूट", "लूटा", "लुटले", "जबरी चोरी"],
    "extortion": ["फिरौती", "वसूली", "खंडणी", "ब्लैकमेल"],
    "cheating": ["धोखा", "धोखाधड़ी", "ठगी", "ठग लिया", "फसवणूक", "फसवले", "फसवणुक", "ओटीपी", "ओ.टी.पी."],
    "impersonation": ["बनकर", "असल्याचे सांगून", "नकली पुलिस", "तोतया"],
    "breach_of_trust": ["गबन", "विश्वासघात", "अपहार"],
    "forgery": ["जाली", "फर्जी दस्तावेज", "नकली दस्तावेज", "बनावट कागद", "बनावट सही"],
    "mischief": ["तोड़फोड़", "नुकसान पहुँचाया", "तोडफोड"],
    "intimidation": ["धमकी", "धमकाया", "धमकावले"],
    "defamation": ["बदनाम", "मानहानि", "बदनामी"],
    "insult_peace": ["गाली", "शिवीगाळ", "शिवी"],
    "rioting": ["दंगा", "भीड़", "दंगल", "जमावाने"],
    "trespass": ["जबरदस्ती घुस", "घर में घुस", "घरात घुस", "अतिक्रमण"],
    "abetment_suicide": ["आत्महत्या के लिए उकसा", "आत्महत्येस प्रवृत्त"],
    "dowry_death": ["दहेज हत्या", "हुंडाबळी"],
}

HINTS = {
    "weapon": (["चाकू", "छुरा", "बंदूक", "पिस्तौल", "लाठी", "डंडा", "रॉड", "तलवार", "कुल्हाड़ी", "तेज़ाब", "चाकूने", "काठी", "कोयता", "बंदूकीने", "सळई"], "Yes"),
    "online": (["ऑनलाइन", "यूपीआई", "ओटीपी", "व्हाट्सएप", "व्हॉट्सॲप", "लिंक", "ऐप", "फ़ोन कॉल", "फोन कॉल", "बैंक खाते", "बँक खात्या"], "Yes"),
    "night": (["रात", "रात्री", "आधी रात", "मध्यरात्री"], "Yes"),
    "death": (["मौत", "मृत्यु", "मर गया", "मर गई", "मृत्यू", "मरण पावला", "मरण पावली"], "Yes"),
}
POLICE = [(["एफआईआर दर्ज नहीं", "रिपोर्ट नहीं लिखी", "मना कर दिया", "एफआयआर नोंदवली नाही", "नकार दिला"], "Yes, but police refused to register an FIR"),
          (["एफआईआर दर्ज", "एफआयआर नोंदवली", "रिपोर्ट दर्ज"], "Yes, FIR registered")]
INJURY = [(["हड्डी टूट", "फ्रैक्चर", "अस्पताल में भर्ती", "टांके", "हाड मोडले", "रुग्णालयात दाखल", "टाके", "बेहोश"],
           "Serious injury (fracture, deep wound, hospitalisation)"),
          (["खरोंच", "नील पड़", "मामूली चोट", "खरचटले", "किरकोळ"], "Simple injury (bruises, minor cuts)")]
RELATION = [(["पति", "ससुराल", "सास", "ससुर", "नवरा", "पती", "सासू", "सासरे", "सासरच्या"], "Husband / in-laws"),
            (["भाई", "बहन", "पिता", "चाचा", "भाऊ", "बहीण", "वडील", "काका"], "Family member"),
            (["पड़ोसी", "दोस्त", "मकान मालिक", "सहकर्मी", "शेजारी", "मित्र", "घरमालक"], "Acquaintance / colleague"),
            (["अजनबी", "अनजान", "अनोळखी"], "Stranger")]
GROUP = [(["कई लोग", "पाँच लोग", "भीड़", "गिरोह", "पाच जणांनी", "अनेक जणांनी", "टोळी"], "Five or more people"),
         (["दो लोग", "तीन लोग", "चार लोग", "दोन जणांनी", "तीन जणांनी", "चार जणांनी", "दोघांनी", "तिघांनी"], "Two to four people")]
SINCE = re.compile(r"((?:19|20)\d{2})\s*(?:से|पासून)")


def has_devanagari(text: str) -> bool:
    return bool(re.search(r"[ऀ-ॿ]", text))


def normalize(text: str) -> str:
    """Devanagari digits and month names -> ASCII/English, so the date and amount parsers work."""
    t = text.translate(DIGITS)
    for k, v in MONTHS.items():
        t = t.replace(k, v)
    for w in ("रुपयांची", "रुपयांचे", "रुपयांचा", "रुपयांना", "रुपयांनी", "रुपये", "रुपए", "रुपया"):
        t = t.replace(w, " rupees ")
    return t.replace("रु.", " Rs ").replace("₹", " Rs ")


def match(text: str) -> dict[str, list[str]]:
    return {oid: [w for w in words if w in text] for oid, words in OFFENCE_WORDS.items() if any(w in text for w in words)}


def infer(text: str) -> dict:
    out = {}
    for qid, (words, val) in HINTS.items():
        if any(w in text for w in words):
            out[qid] = val
    for table, qid in ((POLICE, "police_status"), (INJURY, "injury"), (RELATION, "relationship"), (GROUP, "accused_count")):
        for words, val in table:
            if any(w in text for w in words):
                out[qid] = val
                break
    for k, v in PLACES.items():
        if k in text:
            out["state"] = v
            break
    return out
