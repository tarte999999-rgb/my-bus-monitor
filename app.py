import os
import time
import requests
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# --- 武田さんが調べてくれた最新のIDを反映 ---
TARGET_BUSES = [
    {
        'name': '120番',
        'keitou': 'c2d5a846-d5ab-41a8-9da6-9ca28e8fa812',
        'course': '632acb21-8c13-4b69-a877-281a4f41002e'
    },
    {
        'name': '28番',
        'keitou': 'c3b057fe-ccf6-41bf-887a-e4150c77c8c8', # 武田さん提供の最新ID
        'course': 'eaaad386-69ff-4723-880a-a112e1de20c0'  # 武田さん提供の最新ID
    }
]

def fetch_bus_locations():
    url = "https://www.busnavi-okinawa.com/top/Location/BusLocation"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }
    
    all_buses = []
    seen_plates = set()
    
    for target in TARGET_BUSES:
        params = {
            'datetime': f"{int((time.time() % 1) * 100):02}",
            'keitouSid': target['keitou'],
            'courseGroupSid': target['course'],
            'courseSid': 'AllStations',
            'courseName': '全停留所表示',
            '_': int(time.time() * 1000)
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                locations = data if isinstance(data, list) else data.get('BusLocationList', [])
                
                for item in locations:
                    plate = item.get('Bus', {}).get('NumberPlate', '不明')
                    if plate in seen_plates: continue
                    
                    pos = item.get('Position', {})
                    lat_raw, lon_raw = pos.get('Latitude'), pos.get('Longitude')
                    
                    if lat_raw and lon_raw:
                        # 測地系補正（沖縄のバスナビ特有のズレを修正）
                        lat = lat_raw - 0.00010695 * lat_raw + 0.000017464 * lon_raw + 0.0046017
                        lon = lon_raw - 0.000046038 * lat_raw - 0.000083043 * lon_raw + 0.010040
                        
                        all_buses.append({'lat': lat, 'lon': lon, 'plate': plate, 'line': target['name']})
                        seen_plates.add(plate)
        except:
            continue
    return all_buses

@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>武田家 バス監視システム v3</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <style>
            body { margin: 0; padding: 0; }
            #map { width: 100%; height: 80vh; }
            #status { height: 20vh; background: #1a1a1a; color: #fff; padding: 10px; font-family: sans-serif; box-sizing: border-box; }
            .legend-item { display: inline-block; margin-right: 15px; font-weight: bold; }
            .dot { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 5px; }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div id="status">
            <div style="margin-bottom:10px;">
                <span class="legend-item"><span class="dot" style="background:#ff4444;"></span>120番</span>
                <span class="legend-item"><span class="dot" style="background:#00c851;"></span>28番</span>
                <span class="legend-item"><span class="dot" style="background:#007bff;"></span>天久バス停</span>
            </div>
            <div id="info">更新中...</div>
        </div>
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script>
            var map = L.map('map').setView([26.235399, 127.686561], 12);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            
            // 天久バス停
            L.circleMarker([26.235399, 127.686561], {radius: 8, fillColor: "#007bff", color: "#fff", weight: 3, fillOpacity: 1}).addTo(map).bindPopup("天久バス停");

            var markers = [];
            async function update() {
                try {
                    const res = await fetch('/api/bus');
                    const data = await res.json();
                    markers.forEach(m => map.removeLayer(m));
                    markers = [];
                    data.forEach(bus => {
                        var color = (bus.line === '120番') ? '#ff4444' : '#00c851';
                        var m = L.circleMarker([bus.lat, bus.lon], {radius: 10, fillColor: color, color: "#fff", weight: 2, fillOpacity: 0.9}).addTo(map).bindPopup(bus.line + " (" + bus.plate + ")");
                        markers.push(m);
                    });
                    document.getElementById('info').innerHTML = new Date().toLocaleTimeString() + " 更新 / 稼働中: " + data.length + "台";
                } catch(e) { document.getElementById('info').innerHTML = "通信エラー"; }
            }
            setInterval(update, 60000);
            update();
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/api/bus')
def api_bus():
    return jsonify(fetch_bus_locations())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))