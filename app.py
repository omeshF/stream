import streamlit as st
import requests
from typing import List, Dict, Optional

# ----------------------------
# CONFIG (same as before)
# ----------------------------
TMDB_KEY = st.secrets["tmdb"]["api_key"]
COUNTRY = "GB"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w300"

BLOCKED_LANGUAGES = {"ta", "hi", "te", "ml", "bn", "pa", "mr", "gu", "kn"}

PROVIDERS = {
    "Netflix": {"label": "Netflix", "homepage": "https://www.netflix.com"},
    "Amazon Prime Video": {"label": "Prime Video", "homepage": "https://www.primevideo.com"},
    "Paramount Plus": {"label": "Paramount+", "homepage": "https://www.paramountplus.com"},
    "All 4": {"label": "Channel 4", "homepage": "https://www.channel4.com"},
    "Channel 4": {"label": "Channel 4", "homepage": "https://www.channel4.com"},
    "Discovery+": {"label": "Discovery+", "homepage": "https://www.discoveryplus.com/gb"},
    "Sky Go": {"label": "Sky UK", "homepage": "https://www.sky.com/watch"},
    "Now TV": {"label": "Sky UK", "homepage": "https://www.nowtv.com"},
    "Samsung TV Plus": {"label": "Samsung TV Plus", "homepage": "https://www.samsung.com/uk/tv-plus/"},
}

TMDB_PROVIDER_NAMES = set(PROVIDERS.keys())
ALL_SERVICE_LABELS = sorted({v["label"] for v in PROVIDERS.values()})

def is_allowed_language(item: Dict) -> bool:
    return item.get("original_language", "").lower() not in BLOCKED_LANGUAGES

# [Keep get_titles_by_service and search_by_title functions identical to previous version]
# (They are unchanged — omitted here for brevity but must be included)

# ----------------------------
# DATA FETCH FUNCTIONS (unchanged)
# ----------------------------
@st.cache_data(ttl=3600)
def get_titles_by_service(media_type: str, service_label: Optional[str] = None, genre_id: Optional[int] = None, limit: int = 12) -> List[Dict]:
    results = []
    page = 1
    while len(results) < limit and page <= 4:
        try:
            if media_type == "movie" and genre_id:
                url = "https://api.themoviedb.org/3/discover/movie"
                params = {"api_key": TMDB_KEY, "language": "en-GB", "with_genres": genre_id, "page": page}
            else:
                url = f"https://api.themoviedb.org/3/{'tv' if media_type == 'tv' else 'movie'}/popular"
                params = {"api_key": TMDB_KEY, "language": "en-GB", "page": page}

            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                break

            for item in resp.json().get("results", []):
                if len(results) >= limit or not item.get("poster_path") or not is_allowed_language(item):
                    continue

                media_id = item["id"]
                watch_resp = requests.get(
                    f"https://api.themoviedb.org/3/{'tv' if media_type == 'tv' else 'movie'}/{media_id}/watch/providers",
                    params={"api_key": TMDB_KEY},
                    timeout=10
                )
                if watch_resp.status_code != 200:
                    continue

                providers_data = watch_resp.json().get("results", {}).get(COUNTRY, {})
                matched_service = None
                deep_link = None

                for offer_type in ["flatrate", "free"]:
                    for p in providers_data.get(offer_type, []):
                        tmdb_name = p.get("provider_name")
                        if tmdb_name in TMDB_PROVIDER_NAMES:
                            label = PROVIDERS[tmdb_name]["label"]
                            if service_label is None or label == service_label:
                                matched_service = label
                                deep_link = p.get("web_url") or p.get("url") or PROVIDERS[tmdb_name]["homepage"]
                                break
                    if matched_service:
                        break

                if matched_service:
                    results.append({
                        "title": item.get("title") or item.get("name", "Unknown"),
                        "year": (item.get("release_date") or item.get("first_air_date", ""))[:4],
                        "poster": POSTER_BASE_URL + item["poster_path"],
                        "service": matched_service,
                        "url": deep_link,
                        "type": "TV Show" if media_type == "tv" else ("Documentary" if genre_id == 99 else "Movie")
                    })
            page += 1
        except Exception:
            break
    return results

@st.cache_data(ttl=600)
def search_by_title(query: str) -> List[Dict]:
    results = []
    try:
        resp = requests.get(
            "https://api.themoviedb.org/3/search/multi",
            params={"api_key": TMDB_KEY, "query": query, "include_adult": False, "language": "en-GB"},
            timeout=10
        )
        if resp.status_code != 200:
            return results

        for item in resp.json().get("results", [])[:5]:
            if not is_allowed_language(item):
                continue
            media_id = item.get("id")
            if not media_id:
                continue

            media_type = "tv" if item.get("media_type") == "tv" else "movie"
            watch_resp = requests.get(
                f"https://api.themoviedb.org/3/{media_type}/{media_id}/watch/providers",
                params={"api_key": TMDB_KEY},
                timeout=10
            )
            if watch_resp.status_code != 200:
                continue

            providers_data = watch_resp.json().get("results", {}).get(COUNTRY, {})
            for offer_type in ["flatrate", "free"]:
                for p in providers_data.get(offer_type, []):
                    tmdb_name = p.get("provider_name")
                    if tmdb_name in TMDB_PROVIDER_NAMES:
                        label = PROVIDERS[tmdb_name]["label"]
                        deep_link = p.get("web_url") or p.get("url") or PROVIDERS[tmdb_name]["homepage"]
                        results.append({
                            "title": item.get("title") or item.get("name", "Unknown"),
                            "year": (item.get("release_date") or item.get("first_air_date", ""))[:4],
                            "poster": POSTER_BASE_URL + item["poster_path"] if item.get("poster_path") else None,
                            "service": label,
                            "url": deep_link,
                            "type": "TV Show" if media_type == "tv" else "Movie"
                        })
                        break
    except Exception:
        pass
    return results

# ----------------------------
# SESSION STATE
# ----------------------------
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "selected_service" not in st.session_state:
    st.session_state.selected_service = None

# ----------------------------
# HOME BUTTON HANDLER
# ----------------------------
def go_home():
    st.session_state.search_query = ""
    st.session_state.selected_service = None
    st.experimental_rerun()  # 🔁 Force full reset

# ----------------------------
# UI
# ----------------------------
st.set_page_config(page_title="🎬 Where to Watch UK", layout="wide")
st.title("🎬 Where to Watch in the UK")
st.caption("English content only • UK services")

# Service buttons
cols = st.columns(len(ALL_SERVICE_LABELS))
for idx, service in enumerate(ALL_SERVICE_LABELS):
    with cols[idx]:
        if st.button(service, use_container_width=True, key=f"svc_{service}"):
            st.session_state.selected_service = service
            st.session_state.search_query = ""
            st.experimental_rerun()

# Home button
if st.button("🏠 Home", key="home_btn"):
    go_home()

# Search bar — mic appears automatically on mobile Chrome/Safari (HTTPS)
query = st.text_input(
    "🔍 Search (English only):",
    value=st.session_state.search_query,
    placeholder="Type or tap mic (mobile) → e.g., Friends",
    key="search_input"  # This key is required for state sync
)
st.session_state.search_query = query

# Render content
if st.session_state.search_query:
    st.markdown("---")
    st.subheader(f"Results for: *{st.session_state.search_query}*")
    results = search_by_title(st.session_state.search_query)
    if results:
        for item in results:
            col1, col2 = st.columns([1, 3])
            with col1:
                if item["poster"]:
                    st.image(item["poster"], use_container_width=True)
            with col2:
                st.markdown(f"### [{item['title']} ({item['year']})]({item['url']})")
                st.caption(f"{item['service']} • {item['type']}")
            st.divider()
    else:
        st.warning("No English results found.")

elif st.session_state.selected_service:
    service = st.session_state.selected_service
    st.markdown(f"## 🎬 On {service}")
    for section_name, media_type, genre_id in [
        ("Movies", "movie", None),
        ("TV Shows", "tv", None),
        ("Documentaries", "movie", 99)
    ]:
        st.markdown(f"### {section_name}")
        items = get_titles_by_service(media_type, service, genre_id, limit=6)
        if items:
            cols = st.columns(min(3, len(items)))
            for idx, item in enumerate(items):
                with cols[idx % 3]:
                    st.image(item["poster"], use_container_width=True)
                    st.caption(f"[{item['title']} ({item['year']})]({item['url']})")
        else:
            st.caption(f"No {section_name.lower()} on {service}.")

else:
    # Homepage
    for section_name, media_type, genre_id in [
        ("## 🎬 Top English Movies", "movie", None),
        ("## 📺 Top English TV Shows", "tv", None),
        ("## 🌍 Top English Documentaries", "movie", 99)
    ]:
        st.markdown(section_name)
        items = get_titles_by_service(media_type, None, genre_id, limit=6)
        if items:
            cols = st.columns(min(6, len(items)))
            for idx, item in enumerate(items):
                with cols[idx % 6]:
                    st.image(item["poster"], use_container_width=True)
                    st.caption(f"[{item['title']} ({item['year']})]({item['url']})")
                    st.caption(item["service"])
        else:
            st.info(f"No {section_name.replace('#', '').strip().lower()} found.")

st.markdown("---")
st.caption("• On mobile? Tap the mic icon in the search bar to speak •")