import streamlit as st
import requests

TMDB_KEY = st.secrets["tmdb"]["api_key"]  # Add to Streamlit Secrets

def find_where_to_watch(title, country="GB"):
    # Step 1: Search title
    search = requests.get(
        "https://api.themoviedb.org/3/search/multi",
        params={"api_key": TMDB_KEY, "query": title, "include_adult": False}
    ).json()
    
    results = []
    for item in search.get("results", [])[:3]:
        media_type = "tv" if item.get("media_type") == "tv" else "movie"
        media_id = item["id"]
        
        # Step 2: Get providers
        providers = requests.get(
            f"https://api.themoviedb.org/3/{media_type}/{media_id}/watch/providers",
            params={"api_key": TMDB_KEY}
        ).json()
        
        gb = providers.get("results", {}).get(country, {})
        flatrate = [p["provider_name"] for p in gb.get("flatrate", [])]
        free = [p["provider_name"] for p in gb.get("free", [])]
        
        results.append({
            "title": item.get("title") or item.get("name"),
            "year": (item.get("release_date") or item.get("first_air_date", ""))[:4],
            "type": media_type,
            "on": flatrate + free
        })
    return results

# Your UK services (as named by TMDB)
MY_SERVICES = {"Netflix", "Amazon Prime Video", "Paramount Plus", "Channel 4", "Sky Go"}

st.title("🎬 Where to Watch in the UK?")
query = st.text_input("Enter title:", "Friends")

if query:
    for show in find_where_to_watch(query):
        available = [s for s in show["on"] if s in MY_SERVICES]
        st.subheader(f"{show['title']} ({show['year']})")
        if available:
            st.success(f"✅ On: {', '.join(available)}")
        else:
            st.info("Not on your services")
        st.divider()