import os
import json
import subprocess
import requests
import threading
import time
from flask import Flask, jsonify, request, send_from_directory
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import geonamescache
from generate_locations import generate_locations

app = Flask(__name__, static_url_path='')

LOCATION_CACHE_FILE = 'location_cache.json'
location_cache = {}
failed_lookups = set()

processed_servers = []
processing_lock = threading.Lock()

gc = geonamescache.GeonamesCache()
cities_by_name = {}

CITY_ALIASES = {
    "new york": "new york city",
    "frankfurt": "frankfurt am main",
    "st. louis": "saint louis",
    "montreal": "montréal",
    "reykjavik": "reykjavík",
    "sao paulo": "são paulo",
    "zurich": "zürich",
    "quebec": "québec"
}

COUNTRY_FIXES = {
    "UK": "GB",
    "USA": "US"
}

def setup_offline_geocoding():
    print("Loading offline city database...", flush=True)
    cities = gc.get_cities()
    for city_id, city_data in cities.items():
        name = city_data['name'].lower()
        country = city_data['countrycode']
        key = f"{name}, {country}"
        cities_by_name[key] = {
            "lat": float(city_data['latitude']), 
            "lon": float(city_data['longitude'])
        }
    print(f"Offline database loaded ({len(cities_by_name)} cities).", flush=True)

geolocator = Nominatim(user_agent="iperf3-map-app", timeout=10)

def load_cache():
    global location_cache
    if os.path.exists(LOCATION_CACHE_FILE):
        try:
            with open(LOCATION_CACHE_FILE, 'r') as f:
                location_cache = json.load(f)
        except:
            location_cache = {}
    
    if os.path.exists('prefilled_locations.json'):
        try:
            with open('prefilled_locations.json', 'r') as f:
                static_cache = json.load(f)
                for k, v in static_cache.items():
                    if k not in location_cache:
                        location_cache[k] = v
        except Exception as e:
            print(f"Error loading prefilled locations: {e}")

def save_cache():
    with open(LOCATION_CACHE_FILE, 'w') as f:
        json.dump(location_cache, f)

def get_coordinates(city, country):
    
    if country in COUNTRY_FIXES:
        country = COUNTRY_FIXES[country]

    key = f"{city}, {country}"
    
    if key in location_cache:
        return location_cache[key]
    
    if key in failed_lookups:
        return None

    city_lower = city.lower()
    if city_lower in CITY_ALIASES:
        search_city = CITY_ALIASES[city_lower]
    else:
        search_city = city_lower

    offline_key = f"{search_city}, {country}"
    if offline_key in cities_by_name:
        print(f"Found offline: {key} (via {offline_key})", flush=True)
        coords = cities_by_name[offline_key]
        location_cache[key] = coords
        save_cache()
        return coords

    try:
        print(f"Geocoding online: {key}...", flush=True)
        search_key = f"{search_city}, {country}"
        
        location = geolocator.geocode(search_key)
        if location:
            coords = {"lat": location.latitude, "lon": location.longitude}
            location_cache[key] = coords
            save_cache()
            time.sleep(1.1)
            return coords
        else:
             print(f"Could not find location for: {key}", flush=True)
             failed_lookups.add(key)
    except Exception as e:
        print(f"Error geocoding {key}: {e}", flush=True)
    
    return None

def update_servers_background():
    global processed_servers
    
    if not cities_by_name:
        setup_offline_geocoding()

    print("Starting background server update...", flush=True)
    url = "https://export.iperf3serverlist.net/listed_iperf3_servers.json"
    
    try:
        print(f"Fetching {url}...", flush=True)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        servers = response.json()
        print(f"Fetched {len(servers)} servers.", flush=True)
        
        load_cache()
        
        temp_processed = []
        
        for server in servers:
            city = server.get('SITE')
            country = server.get('COUNTRY')
            if not city or not country:
                continue
                
            key = f"{city}, {country}"
            
            if key in location_cache:
                server['lat'] = location_cache[key]['lat']
                server['lon'] = location_cache[key]['lon']
                temp_processed.append(server)
                
        with processing_lock:
            processed_servers = list(temp_processed)
            
        print(f"Initial load: {len(processed_servers)} servers from cache.", flush=True)

        changes_made = False
        for server in servers:
            city = server.get('SITE')
            country = server.get('COUNTRY')
            
            if not city or not country:
                continue
            
            if 'lat' in server: 
                continue

            key = f"{city}, {country}"
            if key in location_cache:
                 server['lat'] = location_cache[key]['lat']
                 server['lon'] = location_cache[key]['lon']
                 with processing_lock:
                     processed_servers.append(server)
                 continue

            coords = get_coordinates(city, country)
            
            if coords:
                server['lat'] = coords['lat']
                server['lon'] = coords['lon']
                
                with processing_lock:
                     processed_servers.append(server)
                changes_made = True
        
        print("Background update finished.", flush=True)
        
    except Exception as e:
        print(f"Error in background update: {e}")

update_thread = threading.Thread(target=update_servers_background, daemon=True)
update_thread.start()

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/servers')
def get_servers():
    with processing_lock:
        return jsonify(processed_servers)

@app.route('/api/update-locations', methods=['POST'])
def update_locations_endpoint():
    try:
        generate_locations()
        
        load_cache()
        
        threading.Thread(target=update_servers_background, daemon=True).start()
        
        return jsonify({"message": "Locations updated successfully! Server list is refreshing."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test', methods=['POST'])
def run_test():
    data = request.json
    host = data.get('host')
    port = data.get('port')
    flags = data.get('flags', '')
    
    if not host:
        return jsonify({"error": "Host is required"}), 400
    
    if any(c in host for c in [';', '&', '|', ' ']): 
        return jsonify({"error": "Invalid host format"}), 400
        
    cmd = ["iperf3", "-c", host, "-p", str(port) if port else "5201"]
    
    if flags:
        if any(c in flags for c in [';', '&', '|']):
             return jsonify({"error": "Invalid flags"}), 400
        
        for flag in flags.split():
            cmd.append(flag)
            
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
            
        return jsonify({"output": output})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Test timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    load_cache()
    app.run(host='0.0.0.0', port=5000, debug=True)
