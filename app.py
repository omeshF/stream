import streamlit as st
import requests
from typing import List, Dict

# ----------------------------
# CONFIGURATION
# ----------------------------
TMDB_KEY = st.secrets["tmdb"]["api_key"]
COUNTRY = "GB"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w300"

BLOCKED_LANGUAGES = {"ta", "hi", "te", "ml", "bn", "pa", "mr", "gu", "kn"}

SERVICE_HOMEPAGES = {
    "Netflix": "https://www.netflix.com",
    "Amazon Prime Video": "https://www.primevideo.com",
    "Paramount Plus": "https://www.paramountplus.com",
    "All 4": "https://www.channel4.com",
    "Channel 4": "https://www.channel4.com",
    "Discovery+": "https://www.discoveryplus.com/gb",
    "Sky Go": "https://www.sky.com/watch",
    "Now TV": "https://www.nowtv.com",
    "Samsung TV Plus": "https://www.samsung.com/uk/tv-plus/"
}

YOUR_TMDB_SERVICES = set(SERVICE_HOMEPAGES.keys())

SERVICE_LABELS = {
    "Netflix": "Netflix",
    "Amazon Prime Video": "Prime Video",
    "Paramount Plus": "Paramount+",
    "All 4": "Channel 4",
    "Channel 4": "Channel 4",
    "Discovery+": "Discovery+",
    "Sky Go": "Sky UK",
    "Now TV": "Sky UK",
    "Samsung TV Plus": "Samsung TV Plus"
}

def is_allowed_language(item: Dict) -> bool:
    return item.get("original_language", "").lower() not in BLOCKED_LANGUAGES

# ----------------------------
# FETCH DATA FUNCTIONS
# ----------------------------
@st.cache_data(ttl=3600)
def get_titles_by_type(media_type: str, genre_id: int = None, limit: int = 12) -> List[Dict]:
    results = []
    page = 1
    while len(results) < limit and page <= 3:
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
                title = item.get("title") or item.get("name", "Unknown")
                year = (item.get("release_date") or item.get("first_air_date", ""))[:4]
                poster = POSTER_BASE_URL + item["poster_path"]

                watch_resp = requests.get(
                    f"https://api.themoviedb.org/3/{'tv' if media_type == 'tv' else 'movie'}/{media_id}/watch/providers",
                    params={"api_key": TMDB_KEY},
                    timeout=10
                )
                if watch_resp.status_code != 200:
                    continue

                providers_data = watch_resp.json().get("results", {}).get(COUNTRY, {})
                available_links = {}

                for offer_type in ["flatrate", "free"]:
                    for p in providers_data.get(offer_type, []):
                        name = p.get("provider_name")
                        if name in YOUR_TMDB_SERVICES:
                            deep_link = p.get("web_url") or p.get("url")
                            final_url = deep_link if deep_link else SERVICE_HOMEPAGES.get(name)
                            label = SERVICE_LABELS[name]
                            available_links[label] = final_url

                if available_links:
                    results.append({
                        "title": title,
                        "year": year,
                        "poster": poster,
                        "available_links": available_links,
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
            title = item.get("title") or item.get("name", "Unknown")
            year = (item.get("release_date") or item.get("first_air_date", ""))[:4]
            poster = POSTER_BASE_URL + item["poster_path"] if item.get("poster_path") else None

            watch_resp = requests.get(
                f"https://api.themoviedb.org/3/{media_type}/{media_id}/watch/providers",
                params={"api_key": TMDB_KEY},
                timeout=10
            )
            if watch_resp.status_code != 200:
                continue

            providers_data = watch_resp.json().get("results", {}).get(COUNTRY, {})
            available_links = {}

            for offer_type in ["flatrate", "free"]:
                for p in providers_data.get(offer_type, []):
                    name = p.get("provider_name")
                    if name in YOUR_TMDB_SERVICES:
                        deep_link = p.get("web_url") or p.get("url")
                        final_url = deep_link if deep_link else SERVICE_HOMEPAGES.get(name)
                        label = SERVICE_LABELS[name]
                        available_links[label] = final_url

            if available_links:
                results.append({
                    "title": title,
                    "year": year,
                    "poster": poster,
                    "available_links": available_links,
                    "type": "TV Show" if media_type == "tv" else "Movie"
                })
    except Exception:
        pass
    return results

# ----------------------------
# MAIN APP
# ----------------------------
st.set_page_config(page_title="🎬 Where to Watch UK", layout="wide")

# Initialize session state for query
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# Title and subtitle
st.title("🎬 Where to Watch in the UK")
st.markdown("### Watch English shows on **Netflix, Prime, Paramount+, Channel 4, Discovery+, Sky & Samsung TV Plus**")

# Search input
query = st.text_input(
    "🔍 Search by title (English only):",
    value=st.session_state.search_query,
    placeholder="e.g., Friends, The Bear",
    key="search_input"
)

# Update session state
st.session_state.search_query = query

# Home button (only show when user is in search)
if st.session_state.search_query:
    if st.button("🏠 Back to Home"):
        st.session_state.search_query = ""
        st.rerun()

# Show search results or homepage
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
                st.markdown(f"### {item['title']} ({item['year']})")
                st.caption(f"**{item['type']}**")
                st.markdown("**Available on:**")
                for service, url in item["available_links"].items():
                    if url:
                        st.markdown(f"- 🎬 [{service}]({url})")
                    else:
                        st.markdown(f"- {service} (link unavailable)")
            st.divider()
    else:
        st.warning("No English results found on your services.")
else:
    # --- HOMEPAGE SECTIONS ---
    for section_name, media_type, genre_id in [
        ("## 🎬 Top English Movies", "movie", None),
        ("## 📺 Top English TV Shows", "tv", None),
        ("## 🌍 Top English Documentaries", "movie", 99)
    ]:
        st.markdown(section_name)
        items = get_titles_by_type(media_type, genre_id)
        if items:
            cols = st.columns(min(6, len(items)))
            for idx, item in enumerate(items):
                with cols[idx % 6]:
                    st.image(item["poster"], use_container_width=True)
                    st.caption(f"**{item['title']}** ({item['year']})")
                    # Show up to 2 service links
                    for i, (service, url) in enumerate(item["available_links"].items()):
                        if i >= 2:
                            break
                        if url:
                            st.markdown(f"[{service}]({url})")
        else:
            st.info(f"No {section_name.replace('#', '').strip().lower()} found.")

    st.markdown("---")
    st.caption("Deep links to streaming services • English content only • UK")