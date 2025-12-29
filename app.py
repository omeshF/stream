import streamlit as st
import requests
from urllib.parse import quote

# Configuration
COUNTRY = "GB"
YOUR_SERVICES = {
    "Netflix": "nfx",
    "Prime Video": "amp",
    "Paramount+": "pmt",
    "Channel 4": "ch4",
    "Sky UK": "sky",
}

# Reverse map for lookup
ID_TO_SERVICE = {v: k for k, v in YOUR_SERVICES.items()}

def search_justwatch_public(query, country="GB"):
    """Use JustWatch's public search endpoint with browser-like headers."""
    encoded_query = quote(query)
    url = f"https://www.justwatch.com/{country.lower()}/search?q={encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        # First, get the HTML page
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # JustWatch embeds JSON data in the page
        # We'll extract it using string parsing (lightweight alternative to full JS render)
        text = response.text
        if 'id="preloadedData"' in text:
            start = text.find('id="preloadedData">') + len('id="preloadedData">')
            end = text.find('</script>', start)
            json_str = text[start:end].strip()
            if json_str.startswith("{") and json_str.endswith("}"):
                import json
                data = json.loads(json_str)
                items = data.get("data", {}).get("searchTitles", {}).get("edges", [])
                return [edge["node"] for edge in items]
        return []

    except Exception as e:
        st.error(f"⚠️ Search error: {str(e)[:100]}")
        return []

def get_available_on(item):
    """Check which of your services are available."""
    offers = item.get("offers", [])
    available = set()
    for offer in offers:
        pid = str(offer.get("provider_id"))
        if pid in ID_TO_SERVICE:
            available.add(ID_TO_SERVICE[pid])
    return sorted(available)

# App UI
st.title("🎬 Where to Watch? (UK)")
st.caption("Find where your shows/movies stream on Netflix, Prime, Paramount+, Channel 4, or Sky")

query = st.text_input("Enter a movie or TV show title:", placeholder="e.g., Everybody Loves Raymond")

if query:
    with st.spinner("Searching JustWatch..."):
        results = search_justwatch_public(query, COUNTRY)

    if not results:
        st.warning("No results found. Try a more specific title.")
    else:
        for item in results[:5]:
            title = item.get("title") or item.get("originalTitle", "Unknown")
            poster = item.get("posterUrl")
            if poster:
                full_poster = f"https://images.justwatch.com{poster.replace('{{profile}}', 's332')}"
                st.image(full_poster, width=100)

            st.subheader(title)
            item_type = "Movie" if item.get("objectType") == "MOVIE" else "TV Show"
            st.caption(f"Type: {item_type}")

            available = get_available_on(item)
            if available:
                st.success(f"✅ Available on: **{', '.join(available)}**")
            else:
                st.info("Not available on your subscribed services.")

            st.divider()