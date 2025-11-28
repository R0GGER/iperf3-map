# iPERF3 MAP

This project provides a web-based interactive map interface for visualizing and testing public iPerf3 servers. It automatically fetches a list of [public iperf3 servers](https://github.com/R0GGER/public-iperf3-servers), determines their geographic locations, and allows you to run iPerf3 speed tests directly from your browser.

This project is sponsored and supported by <a href="https://cloud.hosthatch.com/a/772" target="_blank">HostHatch</a> and <a href="https://censys.com" target="_blank">Censys</a>.

<img src="screenshots/1.png" alt="iPerf3 Server Map" width="400" />  <img src="screenshots/2.png" alt="iPerf3 Server Map" width="400" />

- **Interactive Map & Testing**: Visualizes iPerf3 servers on a global map using Leaflet.js, allowing you to initiate speed tests directly from the map markers.
- **Automatic Geocoding**: resolving server locations (City/Country) to coordinates using `geonamescache` (offline) and OpenStreetMap's Nominatim (online fallback).
- **Integrated Speed Tests**: Run `iperf3` commands directly from the web interface against any server on the map.

## Quick Start

### Option 1: Docker Compose (Recommended)

Create a `docker-compose.yml` file with the following content:

```yaml
services:
  iperf3-map:
    image: r0gger/iperf3-map
    container_name: iperf3-map
    ports:
      - "5000:5000"
    restart: unless-stopped
```

Start the container:
```bash
docker compose up -d
```

### Option 2: Docker CLI

Run the container directly using the command line:

```bash
docker run -d \
  --name iperf3-map \
  -p 5000:5000 \
  --restart unless-stopped \
  r0gger/iperf3-map
```

## Build and run 
1. **Clone the repository:**
   ```bash
   git clone https://github.com/R0GGER/iperf3-map.git
   cd iperf3-map
   ```

2. **Build and run the container:**
   ```bash
   docker compose up --build -d
   ```

3. **Access the application:**
   Open your browser and navigate to `http://localhost:5000`.

## License

[MIT License](LICENSE) 

