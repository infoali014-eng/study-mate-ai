"""
StudyMate AI – Legacy Theme (Backup)
This is the original ui.py candy-pop theme preserved for rollback.
To rollback: copy content of apply_theme() CSS block back into modules/ui.py's apply_theme().

Backed up: 2026-06-28
Original style: Candy Pop Scholar / Aqua Peach Glass
"""

# Original theme color tokens (kept for reference)
_LEGACY_THEME_PRESETS = {
    "Aqua Peach": {
        "page_bg": (
            "radial-gradient(circle at 8% 12%, rgba(20, 184, 180, 0.16), transparent 24%),"
            "radial-gradient(circle at 92% 10%, rgba(255, 99, 125, 0.14), transparent 22%),"
            "linear-gradient(135deg, #ffffff 0%, #f1fbff 48%, #fff5f7 100%)"
        ),
        "hero_bg": "linear-gradient(135deg, #bdfcf0 0%, #c6efff 52%, #ffd7e2 100%)",
        "accent": "#14b8b4",
        "accent_2": "#ff637d",
    },
    "Lavender Mint": {
        "page_bg": (
            "radial-gradient(circle at 10% 14%, rgba(139, 92, 246, 0.15), transparent 24%),"
            "radial-gradient(circle at 86% 12%, rgba(139, 217, 79, 0.16), transparent 24%),"
            "linear-gradient(135deg, #ffffff 0%, #f5f1ff 48%, #f0fff8 100%)"
        ),
        "hero_bg": "linear-gradient(135deg, #e7dcff 0%, #d9fff4 52%, #f7ffe0 100%)",
        "accent": "#8b5cf6",
        "accent_2": "#14b8b4",
    },
    "Sky Coral": {
        "page_bg": (
            "radial-gradient(circle at 12% 10%, rgba(96, 165, 250, 0.17), transparent 24%),"
            "radial-gradient(circle at 88% 18%, rgba(255, 99, 125, 0.15), transparent 24%),"
            "linear-gradient(135deg, #ffffff 0%, #eff8ff 50%, #fff2f4 100%)"
        ),
        "hero_bg": "linear-gradient(135deg, #d7efff 0%, #dff7ff 48%, #ffd6de 100%)",
        "accent": "#2f7df6",
        "accent_2": "#ff637d",
    },
}

_LEGACY_SUBJECT_THEMES = [
    ("#14b8b4", "#d8fff6", "\U0001f4d8"),
    ("#8b5cf6", "#efe7ff", "\U0001f9ea"),
    ("#2f7df6", "#e3efff", "\U0001f4bb"),
    ("#ff637d", "#ffe3e9", "\U0001f4dd"),
    ("#ffb703", "#fff3c4", "\U0001f4ca"),
    ("#58c84f", "#e8ffd9", "\U0001f331"),
]

_LEGACY_FILE_TYPE_STYLES = {
    "PDF":  ("\U0001f4c4", "#ff637d", "#ffe3e9"),
    "DOCX": ("\U0001f4dd", "#2f7df6", "#e3efff"),
    "PPTX": ("\U0001f4ca", "#ffb703", "#fff3c4"),
    "XLSX": ("\U0001f4ca", "#58c84f", "#e8ffd9"),
    "TXT":  ("\U0001f4c3", "#14b8b4", "#d8fff6"),
    "MD":   ("\U0001f4c3", "#14b8b4", "#d8fff6"),
    "CSV":  ("\U0001f4ca", "#58c84f", "#e8ffd9"),
    "JSON": ("\U0001f9fe", "#8b5cf6", "#efe7ff"),
}

# To restore: Replace modules/ui.py with the original 1958-line version from git history.
# Command: git checkout HEAD~1 -- modules/ui.py
