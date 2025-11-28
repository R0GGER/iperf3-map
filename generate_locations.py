import json
import requests
import time
import geonamescache
import sys
from geopy.geocoders import Nominatim

CITY_ALIASES = {
    "new york": "new york city",
    "frankfurt": "frankfurt am main",
    "st. louis": "saint louis",
    "montreal": "montréal",
    "reykjavik": "reykjavík",
    "sao paulo": "são paulo",
    "zurich": "zürich",
    "quebec": "québec",
    "washington": "washington, d.c."
}

COUNTRY_FIXES = {
    "UK": "GB",
    "USA": "US"
}

def generate_locations():
    print("Fetching server list...")
    url = "https://export.iperf3serverlist.net/listed_iperf3_servers.json"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        servers = response.json()
    except Exception as e:
        print(f"Failed to fetch server list: {e}")
        return

    print(f"Found {len(servers)} servers.")

    gc = geonamescache.GeonamesCache()
    cities = gc.get_cities()
    cities_by_name = {}
    
    print("Loading offline database...")
    for city_id, city_data in cities.items():
        name = city_data['name'].lower()
        country = city_data['countrycode']
        key = f"{name}, {country}"
        cities_by_name[key] = {
            "lat": float(city_data['latitude']), 
            "lon": float(city_data['longitude'])
        }

    geolocator = Nominatim(user_agent="iperf3-map-generator-v2", timeout=10)
    
    unique_keys = set()
    for server in servers:
        city = server.get('SITE')
        country = server.get('COUNTRY')
        if city and country:
            if country in COUNTRY_FIXES:
                country = COUNTRY_FIXES[country]
            unique_keys.add((city, country))
            
    print(f"Found {len(unique_keys)} unique locations to process.")
    
    results = {}
    
    for city, country in unique_keys:
        key = f"{city}, {country}"
        
        city_lower = city.lower()
        search_city = CITY_ALIASES.get(city_lower, city_lower)
        
        offline_key = f"{search_city}, {country}"
        if offline_key in cities_by_name:
            results[key] = cities_by_name[offline_key]
            continue
            
        try:
            search_query = f"{search_city}, {country}"
            print(f"Geocoding online: {search_query}...")
            location = geolocator.geocode(search_query)
            if location:
                results[key] = {
                    "lat": location.latitude,
                    "lon": location.longitude
                }
                print(f"Found: {location.latitude}, {location.longitude}")
                time.sleep(1.1)
            else:
                print(f"Not found online: {search_query}")
        except Exception as e:
            print(f"Error geocoding {key}: {e}")
            
    print(f"Resolved {len(results)} locations.")
    
    sorted_results = dict(sorted(results.items()))
    
    with open('prefilled_locations.json', 'w', encoding='utf-8') as f:
        json.dump(sorted_results, f, indent=2)
        
    print("Saved to prefilled_locations.json")

if __name__ == "__main__":
    sys.stdout = open('gen_log.txt', 'w', encoding='utf-8')
    sys.stderr = sys.stdout
    generate_locations()
