import os
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>武田家 バス監視システム【直通版】</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <style>
            body { margin: 0; padding: 0; }
            #map { width: 100%; height: 85vh; }
            #status { height: 15vh; background: #222; color: #fff; padding: 10px; font-family: sans-serif; box-sizing: border-box; }
            .leaflet-marker-icon { transition: transform 2s linear !important; }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div id="status">
            📡 120番・28番(上り) 監視中...<br>
            <span id="info" style="color:#00ff00;">接続中...</span>
        </div>
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script>
            var map = L.map('map').setView([26.235399, 127.686561], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            L.circleMarker([26.235399, 127.686561], {radius: 8, fillColor: "#007bff", color: "#fff", weight: 3, fillOpacity: 1}).addTo(map).bindPopup("天久バス停");

            var markers = {};
            const targets = [
                {name: '120番', keitou: 'c2d5a846-d5ab-41a8-9da6-9ca28e8fa812', course: '703e7e39-1663-4965-b1a7-1903e1e90956'},
                {name: '28番', keitou: 'c3b057fe-ccf6-41bf-887a-e4150c77c8c8', course: '60689b70-7603-4c57-873b-554477c77f0a'}
            ];

            async function update() {
                let allBuses = [];
                for (let t of targets) {
                    try {
                        const url = `https://www.busnavi-okinawa.com/top/Location/BusLocation?keitouSid=${t.keitou}&courseGroupSid=${t.course}&courseSid=AllStations&_=${Date.now()}`;
                        const res = await fetch(url);
                        const data = await res.json();
                        const locations = Array.isArray(data) ? data : (data.BusLocationList || []);
                        
                        locations.forEach(item => {
                            let lat_raw = item.Position.Latitude;
                            let lon_raw = item.Position.Longitude;
                            // 測地系補正
                            let lat = lat_raw - 0.00010695 * lat_raw + 0.000017464 * lon_raw + 0.0046017;
                            let lon = lon_raw - 0.000046038 * lat_raw - 0.000083043 * lon_raw + 0.010040;
                            allBuses.push({lat: lat, lon: lon, plate: item.Bus.NumberPlate, line: t.name});
                        });
                    } catch(e) { console.error(e); }
                }

                const currentPlates = new Set();
                allBuses.forEach(bus => {
                    currentPlates.add(bus.plate);
                    let color = bus.line === '120番' ? '#ff4444' : '#00c851';
                    if (markers[bus.plate]) {
                        markers[bus.plate].setLatLng([bus.lat, bus.lon]);
                    } else {
                        markers[bus.plate] = L.circleMarker([bus.lat, bus.lon], {
                            radius: 10, fillColor: color, color: "#fff", weight: 2, fillOpacity: 0.9
                        }).addTo(map).bindPopup(bus.line + " (" + bus.plate + ")");
                    }
                });

                Object.keys(markers).forEach(plate => {
                    if (!currentPlates.has(plate)) { map.removeLayer(markers[plate]); delete markers[plate]; }
                });
                document.getElementById('info').textContent = "捕捉: " + allBuses.length + "台 (" + new Date().toLocaleTimeString() + ")";
            }

            setInterval(update, 20000);
            update();
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))