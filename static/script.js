document.addEventListener('DOMContentLoaded', () => {
    const map = L.map('map', { zoomControl: false }).setView([52.13, 5.29], 5);
    L.control.zoom({ position: 'topright' }).addTo(map);

    const openStreetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });

    openStreetMap.addTo(map);

    const modal = document.getElementById('testModal');
    const span = document.getElementsByClassName("close")[0];
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    
    span.onclick = function() {
        modal.style.display = "none";
    }

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    const serversByLocation = {};
    let markersLayer = L.layerGroup().addTo(map);
    const loadingStatus = document.getElementById('loading-status');
    const serverCountSpan = document.getElementById('server-count');

    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(position => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;

            const userIcon = L.divIcon({
                className: 'custom-div-icon',
                html: "<div class='user-marker'>📍</div>",
                iconSize: [30, 30],
                iconAnchor: [15, 30]
            });

            L.marker([lat, lon], { icon: userIcon })
             .addTo(map)
             .openPopup();

        }, error => {
            console.log("Geolocation access denied or failed.", error);
        });
    }

    function loadServers() {
        fetch('/api/servers')
            .then(response => response.json())
            .then(servers => {
                if (servers.length > 0) {
                    loadingStatus.style.display = 'block';
                    serverCountSpan.textContent = servers.length;
                }

                if (servers.length === 0) {
                    console.log("No servers yet, retrying...");
                    setTimeout(loadServers, 3000);
                    return;
                }

                markersLayer.clearLayers();
                
                for (const key in serversByLocation) delete serversByLocation[key];

                servers.forEach(server => {
                    if (server.lat && server.lon) {
                        const key = `${server.lat},${server.lon}`;
                        if (!serversByLocation[key]) {
                            serversByLocation[key] = {
                                lat: server.lat,
                                lon: server.lon,
                                city: server.SITE,
                                country: server.COUNTRY,
                                servers: []
                            };
                        }
                        serversByLocation[key].servers.push(server);
                    }
                });

                Object.values(serversByLocation).forEach(loc => {
                    const starIcon = L.divIcon({
                        className: 'custom-div-icon',
                        html: "<div class='star-marker'>★</div>",
                        iconSize: [30, 30],
                        iconAnchor: [15, 15]
                    });

                    const marker = L.marker([loc.lat, loc.lon], { icon: starIcon });

                    const container = document.createElement('div');
                    const title = document.createElement('h3');
                    title.textContent = `${loc.city}, ${loc.country}`;
                    container.appendChild(title);

                    const list = document.createElement('div');
                    loc.servers.forEach(server => {
                        const item = document.createElement('div');
                        item.className = 'server-list-item';
                        
                        const info = document.createElement('span');
                        info.textContent = `${server.PROVIDER} (${server['IP/HOST']})`;
                        
                        const btn = document.createElement('button');
                        btn.className = 'btn';
                        btn.textContent = 'Select';
                        btn.onclick = () => openTestModal(server);

                        item.appendChild(info);
                        item.appendChild(btn);
                        list.appendChild(item);
                    });
                    container.appendChild(list);

                    marker.bindPopup(container);
                    markersLayer.addLayer(marker);
                });

                if (servers.length < 100) {
                     setTimeout(loadServers, 5000);
                } else {
                    loadingStatus.textContent = `Loaded ${servers.length} servers.`;
                    setTimeout(() => { loadingStatus.style.display = 'none'; }, 3000);
                }
            })
            .catch(err => console.error('Error loading servers:', err));
    }

    loadServers();

    const updateBtn = document.getElementById('update-locations-btn');
    if (updateBtn) {
        updateBtn.onclick = () => {
            if (!confirm("Update locations? This will fetch the latest server list and regenerate the location database. It may take a while.")) return;
            
            const icon = updateBtn.querySelector('i');
            icon.classList.add('fa-spin');
            updateBtn.disabled = true;

            fetch('/api/update-locations', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        alert("Error: " + data.error);
                    } else {
                        alert(data.message);
                        location.reload();
                    }
                })
                .catch(err => alert("Error: " + err))
                .finally(() => {
                    icon.classList.remove('fa-spin');
                    updateBtn.disabled = false;
                });
        };
    }

    function openTestModal(server) {
        modal.style.display = "block";
        modalTitle.textContent = `Test to ${server.SITE} (${server['IP/HOST']})`;
        
        let ports = [];
        if (server.PORT) {
            if (server.PORT.includes('-')) {
                const parts = server.PORT.split('-');
                const start = parseInt(parts[0]);
                const end = parseInt(parts[1]);
                for (let p = start; p <= end; p++) {
                    ports.push(p);
                    if (ports.length > 20) break; 
                }
            } else if (server.PORT.includes(',')) {
                 ports = server.PORT.split(',').map(p => parseInt(p.trim()));
            } else {
                ports = [parseInt(server.PORT)];
            }
        } else {
            ports = [5201];
        }

        let portOptions = ports.map(p => `<option value="${p}">${p}</option>`).join('');

        modalBody.innerHTML = `
            <div style="margin-bottom: 15px;">
                <div style="margin-bottom: 5px;">
                    <strong>Provider:</strong> ${server.PROVIDER}
                </div>
                <div style="margin-bottom: 5px;">
                    <strong>Host:</strong> ${server['IP/HOST']}
                </div>
                
                <div style="margin-bottom: 10px; margin-top: 10px;">
                    <label for="port-select"><strong>Port:</strong></label>
                    <select id="port-select" class="form-control" style="padding: 5px;">
                        ${portOptions}
                    </select>
                </div>

                <div style="margin-bottom: 10px;">
                     <label><strong>Options:</strong></label><br>
                     
                     <div style="margin-top: 5px;">
                        <input type="checkbox" id="opt-reverse" checked> 
                        <label for="opt-reverse">Reverse Mode (-R) <span style="color:#666; font-size:0.9em;">(Download test)</span></label>
                     </div>
                     
                     <div style="margin-top: 5px;">
                        <input type="checkbox" id="opt-ipv6"> 
                        <label for="opt-ipv6">IPv6 (-6)</label>
                     </div>

                     <div style="margin-top: 5px;">
                        <label for="opt-custom">Custom flags:</label>
                        <input type="text" id="opt-custom" placeholder="e.g. -u -b 10M" style="padding: 4px; width: 60%;">
                     </div>
                     
                     <div style="margin-top: 5px; font-size: 0.85em; color: #666;">
                        Server suggested options: ${server.OPTIONS || 'None'}
                     </div>
                </div>

            </div>
            <button id="start-test-btn" class="btn" style="font-size: 1.1em; padding: 8px 16px;">Run iperf3 Test</button>
            <div id="test-status" style="margin-top: 15px;"></div>
            <div id="test-output" style="display:none;"></div>
        `;

        const startBtn = document.getElementById('start-test-btn');
        const statusDiv = document.getElementById('test-status');
        const outputDiv = document.getElementById('test-output');
        const portSelect = document.getElementById('port-select');
        const optReverse = document.getElementById('opt-reverse');
        const optIPv6 = document.getElementById('opt-ipv6');
        const optCustom = document.getElementById('opt-custom');

        startBtn.onclick = () => {
            startBtn.disabled = true;
            statusDiv.innerHTML = '<span class="loader"></span> Running test... (this may take 10-20 seconds)';
            outputDiv.style.display = 'none';
            outputDiv.textContent = '';

            const selectedPort = parseInt(portSelect.value);
            let flags = "";
            
            if (optReverse.checked) flags += " -R";
            if (optIPv6.checked) flags += " -6";
            if (optCustom.value) flags += " " + optCustom.value;

            fetch('/api/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    host: server['IP/HOST'],
                    port: selectedPort,
                    flags: flags.trim()
                })
            })
            .then(response => response.json())
            .then(data => {
                startBtn.disabled = false;
                statusDiv.innerHTML = '';
                outputDiv.style.display = 'block';
                
                if (data.error) {
                    outputDiv.textContent = "Error: " + data.error;
                    outputDiv.style.color = 'red';
                } else {
                    outputDiv.textContent = data.output;
                    outputDiv.style.color = '#00ff00';
                }
            })
            .catch(err => {
                startBtn.disabled = false;
                statusDiv.innerHTML = '';
                outputDiv.style.display = 'block';
                outputDiv.textContent = "Network/Server Error: " + err;
                outputDiv.style.color = 'red';
            });
        };
    }
});
