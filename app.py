import streamlit as st
import requests

# Securely load API key from Streamlit Cloud secrets
# DO NOT hardcode the key in source code!
try:
    API_KEY = st.secrets["streaming_availability"]["api_key"]
except KeyError:
    st.error("❌ API key not found. Please configure it in Streamlit Cloud → Secrets.")
    st.stop()

BASE_URL = "https://streaming-availability.p.rapidapi.com/v2/search"
HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "streaming-availability.p.rapidapi.com"
}

# Your UK services (lowercase, as returned by the API)
YOUR_SERVICES = {
    "netflix",
    "prime",
    "paramountplus",
    "channel4",
    "skygo",      # For Sky UK / Now TV
    # "nowtv" may also appear — add if needed
}

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
        "query": query,
        "country": country,
        "output_language": "en",
        "show_type": "all",
        "series_granularity": "show",
        "order_by": "relevance",
        "page": 1
    }
    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("result", [])
    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            st.error("⚠️ Too many requests. Free tier limit reached (100/day).")
        else:
            st.error(f"API error: {e}")
        return []
    except Exception as e:
        st.error(f"Unexpected error: {str(e)[:150]}")
        return []

def get_available_on(item):
    streaming_info = item.get("streamingInfo", {}).get("gb", [])
    available = set()
    for offer in streaming_info:
        service_id = offer.get("service", "").lower()
        if service_id in YOUR_SERVICES or service_id == "nowtv":
            name = SERVICE_NAMES.get(service_id, service_id.upper())
            available.add(name)
    return sorted(available)

# UI
st.title("🎬 Where to Watch in the UK?")
st.caption("Search movies & shows on Netflix, Prime, Paramount+, Channel 4, and Sky")

query = st.text_input("Enter title:", placeholder="e.g., Ted Lasso")

if query:
    with st.spinner("Searching streaming availability..."):
        results = search_title(query)

    if not results:
        st.warning("No results found. Try a different title.")
    else:
        for item in results[:5]:
            title = item.get("title", "Unknown")
            year = item.get("year", "")
            st.subheader(f"{title} ({year})" if year else title)

            # Poster
            poster_path = item.get("posterPath")
            if poster_path:
                st.image(f"https://image.tmdb.org/t/p/w300{poster_path}", width=120)

            # Type
            media_type = "Movie" if item.get("type") == "movie" else "TV Show"
            st.caption(f"Type: {media_type}")

            # Check your services
            available = get_available_on(item)
            if available:
                st.success(f"✅ Available on: **{', '.join(available)}**")
            else:
                st.info("Not available on your subscribed services.")

            st.divider()