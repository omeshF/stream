import streamlit as st
import requests

# Load API key securely
try:
    API_KEY = st.secrets["streaming_availability"]["api_key"]
except KeyError:
    st.error("❌ Missing API key. Add it in Streamlit Cloud → Secrets as 'streaming_availability.api_key'.")
    st.stop()

BASE_URL = "https://streaming-availability.p.rapidapi.com/search/title"
HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "streaming-availability.p.rapidapi.com"
}

# Your UK services (use exact IDs from API response)
YOUR_SERVICES = {"netflix", "prime", "paramountplus", "channel4", "skygo", "nowtv"}

SERVICE_NAMES = {
    "netflix": "Netflix",
    "prime": "Prime Video",
    "paramountplus": "Paramount+",
    "channel4": "Channel 4",
    "skygo": "Sky UK",
    "nowtv": "Now TV"
}

def search_title(query, country="GB"):
    params = {
        "title": query,
        "country": country,
        "show_type": "all",
        "output_language": "en"
    }
    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        # Note: This API returns 200 even with no results, but may return 404 on misconfig
        if response.status_code == 404:
            # Fallback: try with minimal params
            response = requests.get(
                BASE_URL,
                headers=HEADERS,
                params={"title": query, "country": country}
            )
        response.raise_for_status()
        data = response.json()
        return data.get("result", [])
    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            st.error("⚠️ Rate limit exceeded (100 requests/day on free tier).")
        elif response.status_code == 403:
            st.error("❌ Invalid or missing API key.")
        else:
            st.error(f"HTTP error {response.status_code}: {str(e)[:120]}")
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
st.caption("Find your shows on Netflix, Prime, Paramount+, Channel 4, and Sky")

query = st.text_input("Enter a movie or TV show:", placeholder="e.g., Friends")

if query:
    with st.spinner("Searching..."):
        results = search_title(query)

    if not results:
        st.warning("No results found. Try a more specific title (e.g., 'Friends 1994').")
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