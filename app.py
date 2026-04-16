import os
import time
import requests
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# --- 表示したいバス路線の設定リスト ---
# 28番(読谷線)と120番(名護西空港線)をターゲットにします
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
        # 毎回異なるタイムスタンプを生成してキャッシュを回避
        ms_counter = int((time.time() % 1) * 100)
        params = {
            'datetime': f"{ms_counter:02}",
            'keitouSid': target['keitou'],
            'courseGroupSid': target['course'],
            'courseSid': 'AllStations', # 全停留所を対象に検索
            'courseName': '全停留所表示',
            '_': int(time.time() * 1000)
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # データの形式がリスト直下かBusLocationList下にあるかを柔軟に判定
                locations = data if isinstance(data, list) else data.get('BusLocationList', [])
                
                for item in locations:
                    pos = item.get('Position', {})
                    lat_raw = pos.get('Latitude')
                    lon_raw = pos.get('Longitude')
                    
                    if lat_raw and lon_raw:
                        # 日本測地系から世界測地系への簡易補正
                        lat = lat_raw - 0.00010695 * lat_raw + 0.000017464 * lon_raw + 0.0046017
                        lon = lon_raw - 0.000046038 * lat_raw - 0.000083043 * lon_raw + 0.010040
                        
                        all_buses.append({
                            'lat': lat,
                            'lon': lon,
                            'plate': item.get('Bus', {}).get('NumberPlate', '不明'),
                            'line': target['name']
                        })
        except Exception as e:
            print(f"Error fetching {target['name']}: {e}")
            continue
            
    return all_buses

@app.route('/')
def index():
    # 地図の初期位置は「天久バス停」付近に設定
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>武田家 バス監視システム</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <style>
            body { margin: 0; padding: 0; background: #f0f0f0; }
            #map { width: 100%; height: 75vh; border-bottom: 2px solid #ccc; }
            #status { height: 25vh; background: #ffffff; color: #333; padding: 15px; font-family: sans-serif; box-sizing: border-box; }
            .legend { font-size: 14px; margin-bottom: 10px; display: flex; gap: 15px; }
            .dot { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 5px; }
            .red-dot { background-color: #ff4444; }
            .green-dot { background-color: #00c851; }
            h2 { margin: 0 0 10px 0; font-size: 18px; color: #002244; }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div id="status">
            <h2>🚌 運行状況モニタリング</h2>
            <div class="legend">
                <span><span class="dot red-dot"></span>120番</span>
                <span><span class="dot green-dot"></span>28番</span>
            </div>
            <div id="info">読み込み中...</div>
        </div>

        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script>
            var map = L.map('map').setView([26.235399, 127.686561], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(map);
            
            // 自宅付近の天久バス停を青いアイコンで表示
            var homeIcon = L.circleMarker([26.235399, 127.686561], {
                radius: 8, fillColor: "#007bff", color: "#fff", weight: 3, opacity: 1, fillOpacity: 1
            }).addTo(map).bindPopup("<b>天久バス停</b>");

            var busMarkers = [];

            async function update() {
                try {
                    const res = await fetch('/api/bus');
                    const buses = await res.json();
                    
                    // 古いマーカーを消去
                    busMarkers.forEach(m => map.removeLayer(m));
                    busMarkers = [];

                    buses.forEach(bus => {
                        var color = (bus.line === '120番') ? '#ff4444' : '#00c851';
                        var m = L.circleMarker([bus.lat, bus.lon], {
                            radius: 10,
                            fillColor: color,
                            color: "#ffffff",
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.9
                        }).addTo(map).bindPopup("<b>" + bus.line + "</b><br>ナンバー: " + bus.plate);
                        busMarkers.push(m);
                    });
                    
                    document.getElementById('info').innerHTML = 
                        "最終更新: " + new Date().toLocaleTimeString() + "<br>" +
                        "現在捕捉中のバス: " + buses.length + " 台";
                } catch(e) { 
                    document.getElementById('info').innerHTML = "エラー発生: 再試行中...";
                }
            }

            // 1分ごとに自動更新
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