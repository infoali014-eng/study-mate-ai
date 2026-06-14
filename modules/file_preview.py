import base64
import html
from pathlib import Path

import streamlit as st


def file_exists(file_path):
    """Return True when the stored original file path still exists."""
    return bool(file_path) and Path(file_path).is_file()


def get_file_bytes(file_path):
    """Read a file as bytes for preview or download."""
    return Path(file_path).read_bytes()


def get_file_download_button(file_path, label="Download Original File"):
    """Render a Streamlit download button for any stored file."""
    path = Path(file_path)
    st.download_button(
        label=label,
        data=get_file_bytes(path),
        file_name=path.name,
        mime="application/octet-stream",
        use_container_width=True,
    )


def preview_pdf(file_path, height=720):
    """Embed a PDF inside the Streamlit app using a base64 iframe."""
    pdf_bytes = get_file_bytes(file_path)
    if len(pdf_bytes) > 15 * 1024 * 1024:
        st.warning(
            "This PDF is large, so embedded preview is disabled to keep the app responsive. "
            "Use the download button below to open the original file."
        )
        return

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    st.markdown(
        f"""
        <div class="preview-frame">
            <iframe
                src="data:application/pdf;base64,{pdf_base64}"
                width="100%"
                height="{height}"
                type="application/pdf">
            </iframe>
        </div>
        """,
        unsafe_allow_html=True,
    )


def preview_text_file(file_path, max_characters=20000):
    """Show a readable scrollable preview for TXT-like files."""
    text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    preview_text = html.escape(text[:max_characters])

    st.markdown(
        f"""
        <div class="text-preview">
            <pre>{preview_text}</pre>
        </div>
        """,
        unsafe_allow_html=True,
    )


def preview_image(file_path):
    """Display an uploaded image inside the app."""
    st.image(str(file_path), use_container_width=True)


def preview_extracted_text(text, max_characters=20000):
    """Show extracted text in the same scrollable preview style."""
    preview_text = html.escape((text or "")[:max_characters])
    st.markdown(
        f"""
        <div class="text-preview">
            <pre>{preview_text or "No extracted text available."}</pre>
        </div>
        """,
        unsafe_allow_html=True,
    )


def read_text_preview(file_path, max_characters=3000):
    """Read a short text preview from a file if possible."""
    if not file_exists(file_path):
        return ""
    return Path(file_path).read_text(encoding="utf-8", errors="ignore")[:max_characters]
