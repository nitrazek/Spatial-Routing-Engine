import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timezone

URL = "https://www.wtp.waw.pl/parkingi/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

response = requests.get(URL, headers=HEADERS, timeout=15)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

# Each P+R parking is in a div with class "parking"
parking_divs = soup.find_all("div", class_="parking")

features = []

for div in parking_divs:
    # --- Name ---
    title_div = div.find("div", class_="parking-title")
    if not title_div:
        continue
    title_link = title_div.find("a")
    name = title_link.get_text(strip=True) if title_link else title_div.get_text(strip=True)
    url = title_link.get("href", "") if title_link else ""

    # --- GPS coordinates ---
    gps_el = div.find("p", class_="parking-gps")
    lat, lon = None, None
    if gps_el:
        gps_match = re.search(r"([\d.]+),\s*([\d.]+)", gps_el.get_text())
        if gps_match:
            lat = float(gps_match.group(1))
            lon = float(gps_match.group(2))

    # --- Address, parking type, hours (from <p> in parking-excerpt) ---
    address = None
    parking_type = None
    hours = None
    excerpt = div.find("div", class_="parking-excerpt")
    if excerpt:
        for p_tag in excerpt.find_all("p", class_=False):
            p_text = p_tag.get_text(" ", strip=True)
            if not p_text:
                continue
            if re.search(r"Parking\s+(?:wielopoziomowy|jednopoziomowy|naziemny)", p_text, re.IGNORECASE):
                typ_match = re.search(
                    r"((?:Parking\s+)?(?:wielopoziomowy|jednopoziomowy|naziemny)[^c]*?)(?:czynny|Parking czynny|$)",
                    p_text, re.IGNORECASE,
                )
                if typ_match:
                    parking_type = typ_match.group(1).strip().rstrip(",. ")
                hours_match = re.search(r"((?:P|p)arking czynny.*|czynny.*)", p_text, re.IGNORECASE)
                if hours_match:
                    hours = hours_match.group(1).strip().rstrip(",. ")
            elif not address:
                address = p_text

    # --- Capacity ---
    def get_places(cls):
        el = div.find("div", class_=cls)
        if el:
            m = re.search(r"\d+", el.get_text())
            return int(m.group()) if m else None
        return None

    cars = get_places("parking-places-car")
    bikes = get_places("parking-places-bicycle")
    disabled = get_places("parking-places-wheelchair")
    ev = get_places("parking-places-electric")

    # --- Public transport ---
    transport = []
    icons_div = div.find("div", class_="parking-icons")
    if icons_div:
        for svg in icons_div.find_all("svg"):
            label = (svg.get("aria-label") or "").lower()
            if label and label not in transport:
                transport.append(label)

    if lat is None or lon is None:
        continue

    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat],
        },
        "properties": {
            "name": name,
            "address": address,
            "capacity_cars": cars,
            "capacity_bikes": bikes,
            "capacity_disabled": disabled,
            "capacity_ev_chargers": ev,
            "parking_type": parking_type,
            "opening_hours": hours,
            "public_transport": transport or None,
            "source_url": url,
        },
    }
    features.append(feature)

geojson = {
    "type": "FeatureCollection",
    "name": "Parkingi P+R Warszawa",
    "metadata": {
        "source": URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "description": "Parkingi Park & Ride (P+R) w Warszawie – dane z WTP",
    },
    "features": features,
}

print(f"Found {len(features)} P+R parkings\n")

with open("parkingi_pr.geojson", "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)

print("Saved to parkingi_pr.geojson")
