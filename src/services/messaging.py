from typing import Dict, List

def render_message(template: str, context: Dict[str, str]) -> str:
    # Very simple token replacement
    try:
        return template.format(**context)
    except KeyError:
        # Fallback: ignore missing keys
        return template

def rotate_template(templates: List[str], idx: int) -> tuple[int, str]:
    if not templates:
        return 0, ""
    real_idx = idx % len(templates)
    return real_idx, templates[real_idx]