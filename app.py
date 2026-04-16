import os
import time
import requests
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# --- 表示したいバス路線の設定リスト ---
TARGET_BUSES = [
    {
        'name': '120番',
        'keitou': 'c2d5a846-d5ab-41a8-9da6-9ca28e8fa812',
        'course': '632acb21-8c13-4b69-a877-281a4f41002e'
    },
    {
        'name': '28番',
        'keitou': '87c264cc-92e6-427c-9b65-693355325997',
        'course': '13180482-97f2-4467-b50a-471015694a97'
    }
]

def fetch_bus_locations():
    url = "https://www.busnavi-okinawa.com/top/Location/BusLocation"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.busnavi-okinawa.com/top/Location/BusLocation'
    }
    
    all_buses = []
    
    for target in TARGET_BUSES:
        ms_counter = int((time.time() % 1) * 100)
        params = {
            'datetime': f"{ms_counter:02}",
            'keitouSid': target['keitou'],
            'courseGroupSid': target['course'],
            'courseSid': 'AllStations',
            'courseName': '全停留所表示',
            '_': int(time.time() * 1000)
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                locations = data if isinstance(data, list) else data.get('BusLocationList', [])
                for item in locations:
                    pos = item.get('Position', {})
                    lat_raw = pos.get('Latitude')
                    lon_raw = pos.get('Longitude')
                    if lat_raw and lon_raw:
                        # 測地系補正
                        lat = lat_raw - 0.00010695 * lat_raw + 0.000017464 * lon_raw + 0.0046017
                        lon = lon_raw - 0.000046038 * lat_raw - 0.000083043 * lon_raw + 0.010040
                        all_buses.append({
                            'lat': lat,
                            'lon': lon,
                            'plate': item.get('Bus', {}).get('NumberPlate', '不明'),
                            'line': target['name']
                        })
        except:
            continue
    return all_buses

@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>武田家 バス監視システム</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <style>
            body { margin: 0; padding: 0; }
            #map { width: 100%; height: 80vh; }
            #status { height: 20vh; background: #002244; color: white; padding: 15px; font-family: sans-serif; overflow-y: auto; }
            .bus-label { font-weight: bold; padding: 2px 5px; border-radius: 4px; color: white; }
            .label-120 { background: #e60012; }
            .label-28 { background: #009944; }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div id="status">📡 120番 & 28番 監視中...</div>
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script>
            var map = L.map('map').setView([26.235399, 127.686561], 14);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            
            // 天久バス停
            L.marker([26.235399, 127.686561]).addTo(map).bindPopup("天久バス停");

            var busMarkers = [];

            async function update() {
                try {
                    const res = await fetch('/api/bus');
                    const buses = await res.json();
                    
                    busMarkers.forEach(m => map.removeLayer(m));
                    busMarkers = [];

                    buses.forEach(bus => {
                        // 系統によって色を変えるなどの工夫
                        var color = bus.line === '120番' ? 'red' : 'green';
                        var m = L.circleMarker([bus.lat, bus.lon], {
                            radius: 10,
                            fillColor: color,
                            color: "#fff",
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.8
                        }).addTo(map).bindPopup("<b>" + bus.line + "</b><br>車番: " + bus.plate);
                        busMarkers.push(m);
                    });
                    
                    document.getElementById('status').innerHTML = 
                        "最終更新: " + new Date().toLocaleTimeString() + "<br>" +
                        "現在の運行数: " + buses.length + "台";
                } catch(e) { console.error(e); }
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