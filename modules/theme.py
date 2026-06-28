"""
StudyMate AI – Design Tokens & Theme System
Single source of truth for all visual values.
"""

# ─────────────────────────────────────────────────────────────────────────────
# COLOR PALETTE
# ─────────────────────────────────────────────────────────────────────────────
COLORS = {
    # Brand
    "primary":           "#14B8A6",   # Teal
    "primary_dark":      "#0F9D8C",   # Hover teal
    "primary_light":     "#CCFBF1",   # Teal tint background
    "primary_muted":     "#99F6E4",   # Teal soft

    # Neutrals
    "white":             "#FFFFFF",
    "gray_50":           "#F9FAFB",
    "gray_100":          "#F3F4F6",
    "gray_200":          "#E5E7EB",
    "gray_300":          "#D1D5DB",
    "gray_400":          "#9CA3AF",
    "gray_500":          "#6B7280",
    "gray_600":          "#4B5563",
    "gray_700":          "#374151",
    "gray_800":          "#1F2937",
    "gray_900":          "#111827",

    # Semantics
    "background":        "#FFFFFF",
    "surface":           "#F9FAFB",
    "border":            "#E5E7EB",
    "border_focus":      "#14B8A6",
    "text_primary":      "#111827",
    "text_secondary":    "#6B7280",
    "text_muted":        "#9CA3AF",
    "text_on_primary":   "#FFFFFF",

    # Status
    "success":           "#22C55E",
    "success_bg":        "#F0FDF4",
    "success_border":    "#BBF7D0",
    "warning":           "#F59E0B",
    "warning_bg":        "#FFFBEB",
    "warning_border":    "#FDE68A",
    "error":             "#EF4444",
    "error_bg":          "#FEF2F2",
    "error_border":      "#FECACA",
    "info":              "#3B82F6",
    "info_bg":           "#EFF6FF",
    "info_border":       "#BFDBFE",

    # Accent variants for cards
    "accent_teal":       "#14B8A6",
    "accent_teal_bg":    "#F0FDFA",
    "accent_blue":       "#3B82F6",
    "accent_blue_bg":    "#EFF6FF",
    "accent_purple":     "#8B5CF6",
    "accent_purple_bg":  "#F5F3FF",
    "accent_orange":     "#F97316",
    "accent_orange_bg":  "#FFF7ED",
    "accent_rose":       "#F43F5E",
    "accent_rose_bg":    "#FFF1F2",
    "accent_green":      "#22C55E",
    "accent_green_bg":   "#F0FDF4",
}

# ─────────────────────────────────────────────────────────────────────────────
# SPACING SCALE  (follows 4-pt base grid)
# ─────────────────────────────────────────────────────────────────────────────
SPACING = {
    "xs":   "4px",
    "sm":   "8px",
    "md":   "12px",
    "base": "16px",
    "lg":   "20px",
    "xl":   "24px",
    "2xl":  "32px",
    "3xl":  "40px",
    "4xl":  "48px",
    "5xl":  "64px",
}

# ─────────────────────────────────────────────────────────────────────────────
# BORDER RADIUS
# ─────────────────────────────────────────────────────────────────────────────
RADIUS = {
    "sm":   "6px",
    "md":   "8px",
    "lg":   "12px",
    "xl":   "16px",
    "2xl":  "20px",
    "full": "9999px",
}

# ─────────────────────────────────────────────────────────────────────────────
# SHADOWS
# ─────────────────────────────────────────────────────────────────────────────
SHADOW = {
    "sm":   "0 1px 2px rgba(0,0,0,0.05)",
    "md":   "0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.04)",
    "lg":   "0 4px 6px rgba(0,0,0,0.07), 0 10px 20px rgba(0,0,0,0.06)",
    "xl":   "0 8px 16px rgba(0,0,0,0.08), 0 20px 40px rgba(0,0,0,0.06)",
    "focus":"0 0 0 3px rgba(20,184,166,0.2)",
}

# ─────────────────────────────────────────────────────────────────────────────
# ANIMATION DURATIONS
# ─────────────────────────────────────────────────────────────────────────────
ANIMATION = {
    "fast":   "100ms",
    "base":   "200ms",
    "slow":   "300ms",
    "slower": "500ms",
}

# ─────────────────────────────────────────────────────────────────────────────
# TYPOGRAPHY
# ─────────────────────────────────────────────────────────────────────────────
TYPOGRAPHY = {
    "font_family": "'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "font_url":    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",

    # Size scale
    "text_xs":   "0.75rem",    # 12px
    "text_sm":   "0.875rem",   # 14px
    "text_base": "1rem",       # 16px
    "text_lg":   "1.125rem",   # 18px
    "text_xl":   "1.25rem",    # 20px
    "text_2xl":  "1.5rem",     # 24px
    "text_3xl":  "1.875rem",   # 30px
    "text_4xl":  "2.25rem",    # 36px

    # Weight
    "weight_normal":    "400",
    "weight_medium":    "500",
    "weight_semibold":  "600",
    "weight_bold":      "700",
    "weight_extrabold": "800",
}

# ─────────────────────────────────────────────────────────────────────────────
# ICON SIZES
# ─────────────────────────────────────────────────────────────────────────────
ICON_SIZE = {
    "nav":    20,   # Sidebar navigation
    "card":   24,   # Feature/stat cards
    "button": 16,   # Inside buttons
    "status": 14,   # Status chips/badges
    "hero":   32,   # Large hero icons
}

# ─────────────────────────────────────────────────────────────────────────────
# SUBJECT ACCENT COLORS  (deterministic per subject)
# ─────────────────────────────────────────────────────────────────────────────
SUBJECT_ACCENTS = [
    {"accent": "#14B8A6", "bg": "#F0FDFA", "border": "#99F6E4"},
    {"accent": "#8B5CF6", "bg": "#F5F3FF", "border": "#DDD6FE"},
    {"accent": "#3B82F6", "bg": "#EFF6FF", "border": "#BFDBFE"},
    {"accent": "#F43F5E", "bg": "#FFF1F2", "border": "#FECDD3"},
    {"accent": "#F59E0B", "bg": "#FFFBEB", "border": "#FDE68A"},
    {"accent": "#22C55E", "bg": "#F0FDF4", "border": "#BBF7D0"},
]

# ─────────────────────────────────────────────────────────────────────────────
# FILE TYPE COLORS
# ─────────────────────────────────────────────────────────────────────────────
FILE_TYPE_COLORS = {
    "PDF":  {"accent": "#EF4444", "bg": "#FEF2F2", "icon_key": "file-text"},
    "DOCX": {"accent": "#3B82F6", "bg": "#EFF6FF", "icon_key": "file-text"},
    "DOC":  {"accent": "#3B82F6", "bg": "#EFF6FF", "icon_key": "file-text"},
    "PPTX": {"accent": "#F97316", "bg": "#FFF7ED", "icon_key": "layers"},
    "PPT":  {"accent": "#F97316", "bg": "#FFF7ED", "icon_key": "layers"},
    "XLSX": {"accent": "#22C55E", "bg": "#F0FDF4", "icon_key": "grid"},
    "XLS":  {"accent": "#22C55E", "bg": "#F0FDF4", "icon_key": "grid"},
    "TXT":  {"accent": "#6B7280", "bg": "#F9FAFB", "icon_key": "file-text"},
    "MD":   {"accent": "#6B7280", "bg": "#F9FAFB", "icon_key": "file-text"},
    "CSV":  {"accent": "#22C55E", "bg": "#F0FDF4", "icon_key": "grid"},
    "JSON": {"accent": "#8B5CF6", "bg": "#F5F3FF", "icon_key": "code"},
    "PNG":  {"accent": "#8B5CF6", "bg": "#F5F3FF", "icon_key": "image"},
    "JPG":  {"accent": "#8B5CF6", "bg": "#F5F3FF", "icon_key": "image"},
    "JPEG": {"accent": "#8B5CF6", "bg": "#F5F3FF", "icon_key": "image"},
    "WEBP": {"accent": "#8B5CF6", "bg": "#F5F3FF", "icon_key": "image"},
    "MP3":  {"accent": "#F59E0B", "bg": "#FFFBEB", "icon_key": "mic"},
    "WAV":  {"accent": "#F59E0B", "bg": "#FFFBEB", "icon_key": "mic"},
    "M4A":  {"accent": "#F59E0B", "bg": "#FFFBEB", "icon_key": "mic"},
}
