from __future__ import annotations

from typing import Iterable, List, Dict
from .examples import EXAMPLES_BY_CHANNEL


def _join_guidelines(items: Iterable[str]) -> str:
    lines: List[str] = []
    for item in items:
        if not item:
            continue
        lines.append(f"- {item.strip()}")
    return "\n".join(lines) if lines else "- (ingen)"


def build_generation_messages(
    *,
    user_request: str,
    content_type: str,
    tone_guidelines: List[str],
    terminology_guidelines: List[str],
    style_guidelines: List[str],
    content_rules: List[str],
    similar_campaigns: List[str],
    linkedin_context: List[str] | None = None,
    trustpilot_context: List[str] | None = None,
    website_context: List[str] | None = None,
    web_results: List[Dict[str, str]] | None = None,
    web_search_directives: Dict[str, object] | None = None,
) -> list[dict[str, str]]:
    """
    Returns OpenAI chat messages with a dedicated system role and a user message
    that contains brand guidelines, retrieved similar examples (RAG), and output
    instructions, followed by the user's request.
    - ALL brand guidelines are included verbatim (no RAG) and categorized.
    - You are also provided with example of linkeding and facebook campaigns together with newsletters.
    - Rag content is also provided from linkedin and historical newsletters
    """

    # Normalize/validate content type
    allowed_types = {"linkedin", "facebook", "newsletter", "blog"}
    ct = (content_type or "").strip().lower()
    if ct not in allowed_types:
        ct = "linkedin"

    system = (
        "Du er en erfaren marketingtekstforfatter. Skriv overbevisende, brand-\n"
        "konsistent indhold, der nøje følger de angivne brand-retningslinjer.\n"
        "Prioritér klarhed, korthed og overbevisende formuleringer.\n"
        "Opfind ikke fakta. Hvis information mangler, vælg sikre standarder,\n"
        "der forbliver on-brand.\n"
        "Du skal skelne mellem viden fra RAG/brand-retningslinjer (fakta) og\n"
        "kanaleksempler (stil/struktur). Brug aldrig kanaleksempler som faktakilde."
    )

    brand_guidelines = (
        "### Brand-retningslinjer\n\n"
        "#### Tone\n" + _join_guidelines(tone_guidelines) + "\n\n"
        "#### Terminologi\n" + _join_guidelines(terminology_guidelines) + "\n\n"
        "#### Stil\n" + _join_guidelines(style_guidelines) + "\n\n"
        "#### Indholdsregler\n" + _join_guidelines(content_rules)
    )

    # Optional context sections
    opt_sections: List[str] = []

    if linkedin_context:
        ln_lines: List[str] = ["### LinkedIn-kontekst (ordrette uddrag)"]
        for i, txt in enumerate(linkedin_context[:3], start=1):
            ln_lines.append(f"Uddrag {i}:\n" + txt.strip())
        opt_sections.append("\n\n".join(ln_lines))

    # Trustpilot context removed

    if website_context:
        wb_lines: List[str] = ["### Website/blog-uddrag (RAG)"]
        for i, txt in enumerate(website_context[:5], start=1):
            wb_lines.append(f"Uddrag {i}:\n" + txt.strip())
        opt_sections.append("\n\n".join(wb_lines))

    if web_results:
        wr_lines: List[str] = ["### Webresultater (eksterne kilder – faktatjek anbefales)"]
        for i, item in enumerate(web_results[:3], start=1):
            title = item.get("title", "")
            url = item.get("url", "")
            snippet = item.get("snippet", "")
            wr_lines.append(f"Resultat {i}: {title}\n{url}\n{snippet}")
        opt_sections.append("\n\n".join(wr_lines))

    if web_search_directives:
        d_company = str(web_search_directives.get("company") or "").strip()
        d_links = web_search_directives.get("links") or []
        if not isinstance(d_links, list):
            d_links = []
        links_block = "\n".join([f"- {str(u)}" for u in d_links if isinstance(u, str) and u]) if d_links else "(ingen)"
        plan_lines: List[str] = [
            "### Websøgeinstruktioner",
            "- Prioritér officielle kilder: virksomhedens website og sociale profiler.",
            "- Brug brugerens angivne links først.",
            "- Supplér med faktuel baggrundsviden relevant for emnet.",
            "- Indsaml kun verificerbar fakta, og medtag URL-kilder i svaret.",
            "\nForeslåede søgeforespørgsler:",
            f"- '{d_company} site:linkedin.com' og '{d_company} LinkedIn'" if d_company else "- 'site:linkedin.com' virksomhedsprofil",
            f"- '{d_company} site:facebook.com'" if d_company else "- 'site:facebook.com' virksomhedsprofil",
            f"- '{d_company} site:twitter.com OR site:x.com'" if d_company else "- 'site:x.com' virksomhedsprofil",
            f"- 'site:{d_company.lower().replace(' ', '')}.dk' eller 'site:{d_company.lower().replace(' ', '')}.com'" if d_company else "- virksomhedens domæne med 'site:'",
            "- Emnespecifikke fakta: definitioner, tal, og kilder med høj troværdighed.",
            "\nBrugerangivne links (prioritér):\n" + links_block,
        ]
        opt_sections.append("\n".join(plan_lines))

    examples_section_lines: List[str] = ["### Lignende tidligere kampagner (kun til inspiration)"]
    if similar_campaigns:
        for i, txt in enumerate(similar_campaigns[:5], start=1):
            examples_section_lines.append(f"Eksempel {i}:\n" + txt.strip())
    else:
        examples_section_lines.append("(ingen nære match fundet)")
    examples_section = "\n\n".join(examples_section_lines)

    # Channel-specific placeholders/examples
    display_type_map = {"linkedin": "LinkedIn", "facebook": "Facebook", "newsletter": "Nyhedsbrev", "blog": "Blog"}
    display_type = display_type_map.get(ct, ct.capitalize())
    channel_header = f"### Kanal for output\n- Type: {display_type}"
    # Use provided examples literally, but clarify they are for style/tone only.
    raw_examples = EXAMPLES_BY_CHANNEL.get(ct, [])
    # Build examples block. Keep full text for blogs; truncate other channels for safety.
    if ct == "blog":
        selected = raw_examples[:2]
    else:
        selected = [(ex[:1200] + ("…" if len(ex) > 1200 else "")) for ex in raw_examples][:5]
    channel_examples = "### Eksempler for valgt kanal (kun stil/tone, kopier ikke fakta)\n" + "\n\n".join(selected) if selected else ""
    if ct == "linkedin":
        channel_instructions = (
            "- Optimér til LinkedIn: let at skimme, kortfattet og professionelt.\n"
            "- Foretræk 80–180 ord, medmindre andet er angivet.\n"
            "- Brug 2–5 relevante hashtags til sidst.\n"
        )
    elif ct == "facebook":
        channel_instructions = (
            "- Optimér til Facebook: venlig og fællesskabsorienteret.\n"
            "- Foretræk 50–150 ord, medmindre andet er angivet.\n"
            "- Inkludér en tydelig CTA; brug eventuelle emojis sparsomt.\n"
        )
    elif ct == "newsletter":
        channel_instructions = (
            "- Optimér til e-mail/nyhedsbrev: tydelig emnelinje og preheader.\n"
            "- Skriv en kort brødtekst med én primær CTA.\n"
            "- Foretræk 120–300 ord, medmindre andet er angivet.\n"
        )
    else:  # blog
        channel_instructions = (
            "- Optimér til blog: klar struktur med overskrifter og afsnit.\n"
            "- Indled med en tydelig problemformulering eller opsummering.\n"
            "- Brug underoverskrifter og korte afsnit for læsbarhed.\n"
        )

    output_instructions = (
        "### Output-instruktioner\n"
        "- Skriv i brandets tone og stil.\n"
        "- Brug brandets terminologi konsekvent.\n"
        "- Hvis regler konflikter, prioriter Indholdsregler > Terminologi > Tone > Stil.\n"
        "- Lever ét sammenhængende stykke indhold, medmindre andet er angivet.\n"
        "- Hold dig inden for 200–300 ord, medmindre brugeren angiver længde.\n"
        "- RAG-indhold (eksempler fra uploads/websites) kan indeholde faktuel viden.\n"
        "- De viste kanaleksempler er KUN til stil/struktur; kopier ikke fakta.\n"
        + channel_instructions
    )

    user_content = (
        f"{brand_guidelines}\n\n"
        + (("\n\n".join(opt_sections) + "\n\n") if opt_sections else "")
        + f"{examples_section}\n\n"
        + f"{channel_header}\n\n"
        + f"{channel_examples}\n\n"
        + f"### Brugerens forespørgsel\n{user_request.strip()}\n\n"
        + f"{output_instructions}"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


