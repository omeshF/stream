import streamlit as st
import requests

# Securely load API key
try:
    API_KEY = st.secrets["streaming_availability"]["api_key"]
except KeyError:
    st.error("❌ API key missing. Add it in Streamlit Cloud → Secrets.")
    st.stop()

BASE_URL = "https://streaming-availability.p.rapidapi.com/search/basic"
HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "streaming-availability.p.rapidapi.com"
}

YOUR_SERVICES = {"netflix", "prime", "paramountplus", "channel4", "skygo", "nowtv"}

SERVICE_NAMES = {
    "netflix": "Netflix",
    "prime": "Prime Video",
    "paramountplus": "Paramount+",
    "channel4": "Channel 4",
    "skygo": "Sky UK",
    "nowtv": "Now TV"
}

def search_basic(query, country="GB"):
    """
    Use /search/basic for robust, fuzzy title matching.
    """
    params = {
        "query": query,          # free-text query (supports "friends", "friends 1994", etc.)
        "country": country,
        "output_language": "en",
        "show_type": "all"
    }
    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("result", [])
    except requests.exceptions.HTTPError as e:
        status = response.status_code
        if status == 429:
            st.error("⚠️ Free tier limit reached (100 requests/day).")
        elif status == 403:
            st.error("❌ Invalid or missing API key.")
        else:
            st.error(f"API error ({status}): Search failed. Try again.")
        return []
    except Exception as e:
        st.error(f"Unexpected error: {str(e)[:120]}")
        return []

def get_available_on(item):
    offers = item.get("streamingInfo", {}).get("gb", [])
    available = set()
    for offer in offers:
        service = offer.get("service", "").lower()
        if service in YOUR_SERVICES:
            available.add(SERVICE_NAMES.get(service, service.upper()))
    return sorted(available)

# --- UI ---
st.title("🎬 Where to Watch in the UK?")
st.caption("Search movies & shows on Netflix, Prime, Paramount+, Channel 4, and Sky")

query = st.text_input("Enter a title:", placeholder="e.g., Friends, The Bear, Dune")

if query:
    with st.spinner(f"Searching for '{query}'..."):
        results = search_basic(query)

    if not results:
        st.warning("No matches found. Try a different spelling or title.")
    else:
        for item in results[:5]:
            title = item.get("title", "Unknown")
            year = item.get("year", "")
            st.subheader(f"{title} ({year})" if year else title)

            poster = item.get("posterPath")
            if poster:
                st.image(f"https://image.tmdb.org/t/p/w300{poster}", width=110)

            media_type = "Movie" if item.get("type") == "movie" else "TV Show"
            st.caption(f"Type: {media_type}")

            available = get_available_on(item)
            if available:
                st.success(f"✅ Available on: **{', '.join(available)}**")
            else:
                st.info("Not on your subscribed services.")

            st.divider()