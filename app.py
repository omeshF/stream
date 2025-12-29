import streamlit as st
import requests
from typing import List, Dict

# ----------------------------
# CONFIGURATION
# ----------------------------
TMDB_KEY = st.secrets["tmdb"]["api_key"]
COUNTRY = "GB"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w300"

# TMDB provider names that match your UK services
YOUR_TMDB_SERVICES = {
    "Netflix",
    "Amazon Prime Video",
    "Paramount Plus",
    "Channel 4",      # Sometimes appears
    "All 4",          # ✅ Main Channel 4 provider in TMDB
    "Discovery+",     # ✅ Discovery+ UK
    "Sky Go",
    "Now TV",
    "Samsung TV Plus"
}

# Map to clean display names
SERVICE_LABELS = {
    "Netflix": "Netflix",
    "Amazon Prime Video": "Prime Video",
    "Paramount Plus": "Paramount+",
    "Channel 4": "Channel 4",
    "All 4": "Channel 4",        # ✅ Unified label
    "Discovery+": "Discovery+",
    "Sky Go": "Sky UK",
    "Now TV": "Sky UK",
    "Samsung TV Plus": "Samsung TV Plus"
}

# ----------------------------
# TMDB HELPER FUNCTIONS
# ----------------------------

@st.cache_data(ttl=3600)
def get_titles_by_type(media_type: str, genre_id: int = None, limit: int = 12) -> List[Dict]:
    """Fetch popular titles and filter by your UK services."""
    results = []
    page = 1
    attempts = 0
    max_pages = 3
    
    while len(results) < limit and page <= max_pages and attempts < 5:
        try:
            if media_type == "movie" and genre_id:
                url = "https://api.themoviedb.org/3/discover/movie"
                params = {
                    "api_key": TMDB_KEY,
                    "language": "en-GB",
                    "with_genres": genre_id,
                    "page": page
                }
            else:
                url = f"https://api.themoviedb.org/3/{'tv' if media_type == 'tv' else 'movie'}/popular"
                params = {
                    "api_key": TMDB_KEY,
                    "language": "en-GB",
                    "page": page
                }

            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                attempts += 1
                continue

            data = resp.json()
            items = data.get("results", [])
            if not items:
                break

            for item in items:
                if len(results) >= limit:
                    break
                if not item.get("poster_path"):
                    continue

                media_id = item["id"]
                title = item.get("title") or item.get("name", "Unknown")
                year = (item.get("release_date") or item.get("first_air_date", ""))[:4]
                poster = POSTER_BASE_URL + item["poster_path"]

                # Check UK availability
                watch_url = f"https://api.themoviedb.org/3/{'tv' if media_type == 'tv' else 'movie'}/{media_id}/watch/providers"
                watch_resp = requests.get(watch_url, params={"api_key": TMDB_KEY}, timeout=10)
                if watch_resp.status_code != 200:
                    continue

                providers = watch_resp.json().get("results", {}).get(COUNTRY, {})
                available = set()
                for offer_type in ["flatrate", "free"]:
                    for p in providers.get(offer_type, []):
                        name = p.get("provider_name")
                        if name in YOUR_TMDB_SERVICES:
                            available.add(SERVICE_LABELS[name])

                if available:
                    results.append({
                        "title": title,
                        "year": year,
                        "poster": poster,
                        "available_on": sorted(available),
                        "type": "TV Show" if media_type == "tv" else ("Documentary" if genre_id == 99 else "Movie")
                    })
            page += 1
        except Exception:
            attempts += 1
            continue
    return results


@st.cache_data(ttl=600)
def search_by_title(query: str) -> List[Dict]:
    """Search by title and return availability on your services."""
    results = []
    try:
        search_resp = requests.get(
            "https://api.themoviedb.org/3/search/multi",
            params={
                "api_key": TMDB_KEY,
                "query": query,
                "include_adult": False,
                "language": "en-GB"
            },
            timeout=10
        )
        if search_resp.status_code != 200:
            return results

        for item in search_resp.json().get("results", [])[:5]:
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

            providers = watch_resp.json().get("results", {}).get(COUNTRY, {})
            available = set()
            for offer_type in ["flatrate", "free"]:
                for p in providers.get(offer_type, []):
                    name = p.get("provider_name")
                    if name in YOUR_TMDB_SERVICES:
                        available.add(SERVICE_LABELS[name])

            results.append({
                "title": title,
                "year": year,
                "poster": poster,
                "available_on": sorted(available),
                "type": "TV Show" if media_type == "tv" else "Movie"
            })
    except Exception:
        pass
    return results


# ----------------------------
# MAIN APP
# ----------------------------
st.set_page_config(page_title="🎬 Where to Watch UK", layout="wide")
st.title("🎬 Where to Watch in the UK")
st.markdown(
    "### Find movies & shows on **Netflix, Prime, Paramount+, Channel 4, Discovery+, Sky, and Samsung TV Plus**"
)

# --- Search Bar ---
query = st.text_input("🔍 Search by title:", placeholder="e.g., Everybody Loves Raymond, Planet Earth")

if query:
    st.markdown("---")
    st.subheader(f"Search Results for: *{query}*")
    results = search_by_title(query)
    if results:
        for item in results:
            col1, col2 = st.columns([1, 3])
            with col1:
                if item["poster"]:
                    st.image(item["poster"], use_container_width=True)
            with col2:
                st.markdown(f"### {item['title']} ({item['year']})")
                st.caption(f"**{item['type']}**")
                if item["available_on"]:
                    st.success(f"✅ **Available on:** {', '.join(item['available_on'])}")
                else:
                    st.info("Not available on your subscribed services.")
            st.divider()
    else:
        st.warning("No results found. Try a different title.")

# --- Homepage Sections (only if no search) ---
if not query:
    st.markdown("## 🎬 Top Movies")
    movies = get_titles_by_type("movie")
    if movies:
        cols = st.columns(min(6, len(movies)))
        for idx, movie in enumerate(movies):
            with cols[idx % 6]:
                st.image(movie["poster"], use_container_width=True)
                st.caption(f"**{movie['title']}** ({movie['year']})")
                st.caption(", ".join(movie["available_on"]))
    else:
        st.info("No top movies found on your services.")

    st.markdown("## 📺 Top TV Shows")
    tv_shows = get_titles_by_type("tv")
    if tv_shows:
        cols = st.columns(min(6, len(tv_shows)))
        for idx, show in enumerate(tv_shows):
            with cols[idx % 6]:
                st.image(show["poster"], use_container_width=True)
                st.caption(f"**{show['title']}** ({show['year']})")
                st.caption(", ".join(show["available_on"]))
    else:
        st.info("No top TV shows found on your services.")

    st.markdown("## 🌍 Top Documentaries")
    docs = get_titles_by_type("movie", genre_id=99)  # TMDB genre ID for documentaries
    if docs:
        cols = st.columns(min(6, len(docs)))
        for idx, doc in enumerate(docs):
            with cols[idx % 6]:
                st.image(doc["poster"], use_container_width=True)
                st.caption(f"**{doc['title']}** ({doc['year']})")
                st.caption(", ".join(doc["available_on"]))
    else:
        st.info("No documentaries found on your services.")

    st.markdown("---")
    st.caption("Data from TMDB • Updated hourly • UK services only")