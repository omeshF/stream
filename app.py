import streamlit as st
import requests

# Load TMDB API key from secrets
TMDB_KEY = st.secrets["tmdb"]["api_key"]

# Map TMDB provider names to your clean labels
TMDB_TO_YOUR_NAME = {
    "Netflix": "Netflix",
    "Amazon Prime Video": "Prime Video",
    "Paramount Plus": "Paramount+",
    "Channel 4": "Channel 4",
    "Samsung TV Plus": "Samsung TV Plus",
    "Sky Go": "Sky UK",
    "Now TV": "Sky UK",  # Treat Now TV as Sky UK
}

# Set of providers you care about (for fast lookup)
YOUR_SERVICES_TMDB = set(TMDB_TO_YOUR_NAME.keys())

def find_where_to_watch(title, country="GB"):
    results = []
    
    # Step 1: Search for movies/TV shows
    search_resp = requests.get(
        "https://api.themoviedb.org/3/search/multi",
        params={
            "api_key": TMDB_KEY,
            "query": title,
            "include_adult": False,
            "language": "en-US"
        },
        timeout=10
    )
    
    if search_resp.status_code != 200:
        st.error("TMDB search failed.")
        return results
        
    search_data = search_resp.json()
    
    for item in search_data.get("results", [])[:5]:  # Top 5
        media_type = "tv" if item.get("media_type") == "tv" else "movie"
        media_id = item.get("id")
        if not media_id:
            continue
            
        title_display = item.get("title") or item.get("name", "Unknown")
        year = (item.get("release_date") or item.get("first_air_date", ""))[:4]

        # Step 2: Get streaming providers in GB
        watch_resp = requests.get(
            f"https://api.themoviedb.org/3/{media_type}/{media_id}/watch/providers",
            params={"api_key": TMDB_KEY},
            timeout=10
        )
        
        if watch_resp.status_code != 200:
            continue
            
        watch_data = watch_resp.json()
        gb_providers = watch_data.get("results", {}).get(country, {})
        
        # Combine flatrate (subscription) + free (ad-supported)
        all_providers = []
        for p in gb_providers.get("flatrate", []) + gb_providers.get("free", []):
            provider_name = p.get("provider_name")
            if provider_name in YOUR_SERVICES_TMDB:
                all_providers.append(TMDB_TO_YOUR_NAME[provider_name])
        
        # Remove duplicates and sort
        available_on = sorted(set(all_providers))
        
        results.append({
            "title": title_display,
            "year": year,
            "type": "TV Show" if media_type == "tv" else "Movie",
            "available_on": available_on
        })
        
    return results

# --- UI ---
st.set_page_config(page_title="🎬 Where to Watch (UK)", layout="wide")
st.title("🎬 Where to Watch in the UK")
st.caption("Search across Netflix, Prime Video, Paramount+, Channel 4, Sky UK, and Samsung TV Plus")

query = st.text_input("🔍 Enter a movie or TV show title:", placeholder="e.g., Friends, The Great British Bake Off")

if query:
    with st.spinner(f"Searching for '{query}'..."):
        shows = find_where_to_watch(query)
    
    if not shows:
        st.warning("No results found. Try a different title.")
    else:
        for show in shows:
            col1, col2 = st.columns([1, 3])
            with col1:
                # Optional: Add poster later (requires extra TMDB call)
                pass
            with col2:
                st.subheader(f"{show['title']} ({show['year']})")
                st.caption(f"Type: {show['type']}")
                
                if show["available_on"]:
                    services_str = ", ".join(show["available_on"])
                    st.success(f"✅ Available on: **{services_str}**")
                else:
                    st.info("Not available on your subscribed services.")
            st.divider()