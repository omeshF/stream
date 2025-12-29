import streamlit as st
import requests
from itertools import islice

# ----------------------------
# CONFIG
# ----------------------------
TMDB_KEY = st.secrets["tmdb"]["api_key"]
COUNTRY = "GB"

# Your services (as they appear in TMDB)
YOUR_TMDB_SERVICES = {
    "Netflix",
    "Amazon Prime Video",
    "Paramount Plus",
    "Channel 4",
    "Sky Go",
    "Now TV",
    "Samsung TV Plus"
}

# Clean labels for display
SERVICE_LABELS = {
    "Netflix": "Netflix",
    "Amazon Prime Video": "Prime Video",
    "Paramount Plus": "Paramount+",
    "Channel 4": "Channel 4",
    "Sky Go": "Sky UK",
    "Now TV": "Sky UK",
    "Samsung TV Plus": "Samsung TV Plus"
}

POSTER_BASE_URL = "https://image.tmdb.org/t/p/w300"

# ----------------------------
# TMDB HELPERS
# ----------------------------
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_titles_by_type(media_type, genre_id=None, limit=30):
    """
    Fetch popular/trending titles and filter by your services.
    media_type: 'movie' or 'tv'
    genre_id: e.g., 99 = Documentary
    """
    results = []
    
    # Get popular titles
    url = f"https://api.themoviedb.org/3/{'tv' if media_type == 'tv' else 'movie'}/popular"
    params = {"api_key": TMDB_KEY, "language": "en-GB", "page": 1}
    if media_type == "movie" and genre_id:
        url = "https://api.themoviedb.org/3/discover/movie"
        params["with_genres"] = genre_id

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        items = data.get("results", [])
        
        for item in items:
            if len(results) >= 12:  # We only need ~12 per section
                break
                
            media_id = item["id"]
            title = item.get("title") or item.get("name", "Unknown")
            year = (item.get("release_date") or item.get("first_air_date", ""))[:4]
            poster_path = item.get("poster_path")
            
            # Skip if no poster
            if not poster_path:
                continue
                
            # Check availability in GB
            watch_url = f"https://api.themoviedb.org/3/{'tv' if media_type == 'tv' else 'movie'}/{media_id}/watch/providers"
            watch_resp = requests.get(watch_url, params={"api_key": TMDB_KEY}, timeout=10)
            if watch_resp.status_code != 200:
                continue
                
            providers_data = watch_resp.json().get("results", {}).get(COUNTRY, {})
            all_providers = []
            for offer_type in ["flatrate", "free"]:
                for p in providers_data.get(offer_type, []):
                    name = p.get("provider_name")
                    if name in YOUR_TMDB_SERVICES:
                        all_providers.append(SERVICE_LABELS[name])
                        
            if all_providers:
                results.append({
                    "title": title,
                    "year": year,
                    "poster": POSTER_BASE_URL + poster_path,
                    "available_on": sorted(set(all_providers)),
                    "type": "TV Show" if media_type == "tv" else ("Documentary" if genre_id == 99 else "Movie")
                })
    except Exception as e:
        st.error(f"Error fetching {media_type}: {str(e)[:100]}")
        
    return results

# ----------------------------
# APP LAYOUT
# ----------------------------
st.set_page_config(page_title="🎬 Where to Watch UK", layout="wide")
st.title("🎬 Where to Watch in the UK")
st.markdown("### Find movies & shows on **Netflix, Prime, Paramount+, Channel 4, Sky, and Samsung TV Plus**")

# --- Search Bar ---
query = st.text_input("🔍 Search by title:", placeholder="e.g., Friends, Planet Earth")
if query:
    st.markdown("---")
    st.subheader("Search Results")
    # Reuse your existing search function here if needed
    # (For brevity, we’ll focus on homepage — but you can integrate both)

# --- HOMEPAGE SECTIONS ---
st.markdown("## 🎬 Top Movies")
movies = get_titles_by_type("movie")
if movies:
    cols = st.columns(6)
    for idx, movie in enumerate(movies[:6]):
        with cols[idx % 6]:
            st.image(movie["poster"], use_container_width=True)
            st.caption(f"**{movie['title']}** ({movie['year']})")
            st.caption(", ".join(movie["available_on"]))
else:
    st.info("No top movies found on your services.")

st.markdown("## 📺 Top TV Shows")
tv_shows = get_titles_by_type("tv")
if tv_shows:
    cols = st.columns(6)
    for idx, show in enumerate(tv_shows[:6]):
        with cols[idx % 6]:
            st.image(show["poster"], use_container_width=True)
            st.caption(f"**{show['title']}** ({show['year']})")
            st.caption(", ".join(show["available_on"]))
else:
    st.info("No top TV shows found on your services.")

st.markdown("## 🌍 Top Documentaries")
docs = get_titles_by_type("movie", genre_id=99)  # 99 = Documentary
if docs:
    cols = st.columns(6)
    for idx, doc in enumerate(docs[:6]):
        with cols[idx % 6]:
            st.image(doc["poster"], use_container_width=True)
            st.caption(f"**{doc['title']}** ({doc['year']})")
            st.caption(", ".join(doc["available_on"]))
else:
    st.info("No documentaries found on your services.")

# --- Footer ---
st.markdown("---")
st.caption("Data from TMDB • Updated hourly • UK services only")