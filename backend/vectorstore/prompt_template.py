from __future__ import annotations

from typing import Iterable, List, Dict


def _join_guidelines(items: Iterable[str]) -> str:
    lines: List[str] = []
    for item in items:
        if not item:
            continue
        lines.append(f"- {item.strip()}")
    return "\n".join(lines) if lines else "- (none)"


def build_generation_messages(
    *,
    user_request: str,
    tone_guidelines: List[str],
    terminology_guidelines: List[str],
    style_guidelines: List[str],
    content_rules: List[str],
    similar_campaigns: List[str],
    linkedin_context: List[str] | None = None,
    website_context: List[str] | None = None,
) -> list[dict[str, str]]:
    """
    Returns OpenAI chat messages with a dedicated system role and a user message
    that contains brand guidelines, retrieved similar examples (RAG), and output
    instructions, followed by the user's request.
    - ALL brand guidelines are included verbatim (no RAG) and categorized.
    - RAG content is ONLY from historical uploaded campaigns.
    """

    system = (
        "You are an expert marketing copywriter. Generate compelling, brand-\n"
        "consistent marketing copy that strictly follows the provided brand\n"
        "guidelines. Prefer clarity, brevity, and persuasive language.\n"
        "Do not invent facts. If information is missing, proceed with safe defaults\n"
        "that remain on-brand."
    )

    brand_guidelines = (
        "### Brand Guidelines\n\n"
        "#### Tone\n" + _join_guidelines(tone_guidelines) + "\n\n"
        "#### Terminology\n" + _join_guidelines(terminology_guidelines) + "\n\n"
        "#### Style\n" + _join_guidelines(style_guidelines) + "\n\n"
        "#### Content Rules\n" + _join_guidelines(content_rules)
    )

    # Optional context sections
    opt_sections: List[str] = []

    if linkedin_context:
        ln_lines: List[str] = ["### LinkedIn Context (verbatim snippets)"]
        for i, txt in enumerate(linkedin_context[:3], start=1):
            ln_lines.append(f"Snippet {i}:\n" + txt.strip())
        opt_sections.append("\n\n".join(ln_lines))

    # Trustpilot context removed

    if website_context:
        wb_lines: List[str] = ["### Website Blog Excerpts (RAG)"]
        for i, txt in enumerate(website_context[:5], start=1):
            wb_lines.append(f"Excerpt {i}:\n" + txt.strip())
        opt_sections.append("\n\n".join(wb_lines))

    examples_section_lines: List[str] = ["### Similar Past Campaigns (for inspiration only)"]
    if similar_campaigns:
        for i, txt in enumerate(similar_campaigns[:5], start=1):
            examples_section_lines.append(f"Example {i}:\n" + txt.strip())
    else:
        examples_section_lines.append("(no close matches found)")
    examples_section = "\n\n".join(examples_section_lines)

    output_instructions = (
        "### Output Instructions\n"
        "- Write in the brand's tone and style.\n"
        "- Use the brand's terminology consistently.\n"
        "- If rules conflict, prioritize Content Rules > Terminology > Tone > Style.\n"
        "- Provide a single, cohesive piece of content unless asked otherwise.\n"
        "- Keep within 200-300 words unless the user specifies length.\n"
    )

    user_content = (
        f"{brand_guidelines}\n\n"
        + (("\n\n".join(opt_sections) + "\n\n") if opt_sections else "")
        + f"{examples_section}\n\n"
        + f"### User Request\n{user_request.strip()}\n\n"
        + f"{output_instructions}"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


