import streamlit as st
import requests

# Configuration
COUNTRY = "GB"  # United Kingdom
YOUR_SERVICES = {
    "Netflix": "nfx",
    "Prime Video": "amp",
    "Paramount+": "pmt",
    "Channel 4": "ch4",
    "Sky UK": "sky",
}

def search_justwatch(query, country="GB"):
    """Search JustWatch for a title and return offers in the given country."""
    url = "https://apis.justwatch.com/content/titles/en_US/search"
    params = {
        "body": {"query": query},
        "country": country,
        "page": 1,
        "page_size": 5
    }
    try:
        response = requests.post(url, json=params["body"], params={"country": country})
        response.raise_for_status()
        return response.json().get("items", [])
    except Exception as e:
        st.error(f"Search failed: {e}")
        return []

def get_available_on(item, service_ids):
    """Extract which of your services are available for this item."""
    offers = item.get("offers", [])
    available = set()
    for offer in offers:
        provider_id = offer.get("provider_id")
        if provider_id in service_ids:
            # Map ID back to service name
            for name, pid in service_ids.items():
                if pid == provider_id:
                    available.add(name)
    return sorted(available)

# App UI
st.title("🎬 Where to Watch?")
st.caption("Find where your shows/movies are streaming in the UK")

query = st.text_input("Enter a movie or TV show title:")

if query:
    with st.spinner("Searching..."):
        results = search_justwatch(query, COUNTRY)
    
    if not results:
        st.warning("No results found.")
    else:
        for item in results[:5]:  # Show top 5
            title = item.get("title") or item.get("original_title", "Unknown")
            poster = item.get("poster")
            if poster:
                poster_url = f"https://images.justwatch.com{poster.replace('{profile}', 's332')}"
                st.image(poster_url, width=100)
            
            st.subheader(title)
            st.caption(f"Type: {item.get('object_type', '').title()}")
            
            available = get_available_on(item, YOUR_SERVICES)
            if available:
                st.success(f"✅ Available on: {', '.join(available)}")
            else:
                st.info("Not available on your services.")
            
            st.divider()
