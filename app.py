import os
import time
import json
import requests
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# --- 120番バスのデータ取得ロジック ---
def get_bus_data():
    url = "https://www.busnavi-okinawa.com/top/Location/BusLocation"
    ms_counter = int((time.time() % 1) * 100)
    params = {
        'datetime': f"{ms_counter:02}",
        'keitouSid': 'c2d5a846-d5ab-41a8-9da6-9ca28e8fa812',
        'courseGroupSid': '632acb21-8c13-4b69-a877-281a4f41002e',
        'courseSid': 'AllStations',
        'courseName': '全停留所表示',
        '_': int(time.time() * 1000)
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.busnavi-okinawa.com/top/Location/BusLocation'
    }
    
    bus_list = []
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            locations = data if isinstance(data, list) else data.get('BusLocationList', [])
            for item in locations:
                pos = item.get('Position', {})
                raw_lat, raw_lon = pos.get('Latitude'), pos.get('Longitude')
                if raw_lat and raw_lon:
                    # 測地系補正
                    lat = raw_lat - 0.00010695 * raw_lat + 0.000017464 * raw_lon + 0.0046017
                    lon = raw_lon - 0.000046038 * raw_lat - 0.000083043 * raw_lon + 0.010040
                    bus_list.append({'lat': lat, 'lon': lon, 'plate': item.get('Bus', {}).get('NumberPlate', '不明')})
    except:
        pass
    return bus_list

# --- 画面（HTML）を表示するルート ---
@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>武田家 120番バス監視システム</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <style>
            body { margin: 0; padding: 0; }
            #map { width: 100%; height: 85vh; }
            #status { height: 15vh; background: #002244; color: white; padding: 10px; font-family: sans-serif; }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div id="status">📡 120番バス 接続中...</div>
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script>
            var map = L.map('map').setView([26.235399, 127.686561], 15);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            L.marker([26.235399, 127.686561]).addTo(map).bindPopup("天久バス停");
            var busMarkers = [];

            async function update() {
                const res = await fetch('/api/bus');
                const buses = await res.json();
                busMarkers.forEach(m => map.removeLayer(m));
                busMarkers = [];
                buses.forEach(bus => {
                    var m = L.marker([bus.lat, bus.lon], {
                        icon: L.icon({ iconUrl: 'https://cdn-icons-png.flaticon.com/512/3448/3448339.png', iconSize: [35, 35] })
                    }).addTo(map).bindPopup("120番: " + bus.plate);
                    busMarkers.push(m);
                });
                document.getElementById('status').innerHTML = "最終更新: " + new Date().toLocaleTimeString() + "<br>捕捉数: " + buses.length + "台";
            }
            setInterval(update, 60000);
            update();
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

# --- データを渡すAPI ---
@app.route('/api/bus')
def api_bus():
    return jsonify(get_bus_data())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))