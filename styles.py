"""All custom CSS lives here."""
import streamlit as st


def inject(font_px: int = 16) -> None:
    """Inject fonts + CSS (mobile-first, RTL-safe Urdu cards)."""
    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&family=Noto+Naskh+Arabic&display=swap');
.block-container{{padding:1rem .8rem 4rem;max-width:720px}}
.stButton>button,.stDownloadButton>button{{min-height:3rem;border-radius:12px;width:100%;font-size:{font_px}px}}
.card{{background:#fff;color:#12332b;border:1px solid #cfe3dc;border-radius:14px;padding:.9rem 1rem;margin:.5rem 0;font-size:{font_px}px;line-height:1.6}}
.card.ur{{direction:rtl;text-align:right;font-family:'Noto Nastaliq Urdu','Noto Naskh Arabic',serif;line-height:2.3;unicode-bidi:plaintext}}
.card.ok{{border-left:6px solid #1b7f5c;background:#e9f7f1}}
.card.bad{{border-left:6px solid #c0392b;background:#fdecea}}
.card.ur.ok{{border-left:1px solid #cfe3dc;border-right:6px solid #1b7f5c}}
.card.ur.bad{{border-left:1px solid #cfe3dc;border-right:6px solid #c0392b}}
</style>""", unsafe_allow_html=True)
