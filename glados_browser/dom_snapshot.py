from __future__ import annotations

from typing import Any, Dict, List

_SNAPSHOT_JS = """
() => {
  const items = [];
  const sel = 'a, button, input, textarea, select, [role=button], [role=link], [role=textbox]';
  document.querySelectorAll(sel).forEach((el, i) => {
    if (i > 100) return;
    const tag = el.tagName.toLowerCase();
    const text = (
      el.innerText || el.value || el.placeholder ||
      el.getAttribute('aria-label') || el.name || ''
    ).trim().replace(/\\s+/g, ' ').slice(0, 100);
    if (!text && tag !== 'input' && tag !== 'textarea') return;
    const type = el.type || '';
    items.push({ tag, type, text: text || `[${tag}]` });
  });
  const bodyText = (document.body && document.body.innerText || '')
    .replace(/\\s+/g, ' ')
    .trim()
    .slice(0, 5000);
  return { items, bodyText };
}
"""


def capture_page_state(page: Any, *, max_body: int = 4500) -> str:
    """Compact page representation for the planner LLM."""
    try:
        title = page.title()
    except Exception:
        title = ""
    try:
        url = page.url
    except Exception:
        url = ""

    data: Dict[str, Any] = {"items": [], "bodyText": ""}
    try:
        data = page.evaluate(_SNAPSHOT_JS) or data
    except Exception:
        pass

    items: List[Dict[str, str]] = data.get("items") or []
    body = str(data.get("bodyText") or "")[:max_body]

    lines = [f"URL: {url}", f"Title: {title}", "", "Interactive elements:"]
    for i, el in enumerate(items[:60], 1):
        tag = el.get("tag", "?")
        typ = el.get("type", "")
        text = el.get("text", "")
        extra = f" ({typ})" if typ else ""
        lines.append(f"  {i}. <{tag}{extra}> {text}")

    lines.extend(["", "Visible text:", body or "(empty)"])
    return "\n".join(lines)
