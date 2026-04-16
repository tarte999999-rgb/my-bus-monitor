import os
from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    # サーバーを通さず、武田さんのブラウザが直接「バスなび」にデータを聞きに行く仕組み
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>武田家 バス監視システム【究極版】</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <style>
            body { margin: 0; padding: 0; background: #1a1a1a; color: white; }
            #map { width: 100%; height: 80vh; }
            #status { height: 20vh; padding: 15px; font-family: sans-serif; box-sizing: border-box; }
            .info-text { font-size: 1.2em; color: #00ff00; }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div id="status">
            📡 120番・28番 監視中（ブラウザ直結モード）<br>
            <div id="info" class="info-text">データ取得中...</div>
            <div id="debug" style="font-size: 0.8em; color: #aaa; margin-top:5px;"></div>
        </div>
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script>
            var map = L.map('map').setView([26.235399, 127.686561], 12);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            L.circleMarker([26.235399, 127.686561], {radius: 8, fillColor: "#007bff", color: "#fff", weight: 3, fillOpacity: 1}).addTo(map).bindPopup("天久バス停");

            var markers = {};
            const targets = [
                {name: '120番', k: 'c2d5a846-d5ab-41a8-9da6-9ca28e8fa812'},
                {name: '28番', k: 'c3b057fe-ccf6-41bf-887a-e4150c77c8c8'}
            ];

            async function update() {
                let foundAny = 0;
                for (let t of targets) {
                    try {
                        // ブラウザから直接バスなびへ（CORS回避のためproxy等は通さない）
                        const url = `https://www.busnavi-okinawa.com/top/Location/BusLocation?keitouSid=${t.k}&courseGroupSid=AllStations&courseSid=AllStations&_=${Date.now()}`;
                        const res = await fetch(url);
                        const data = await res.json();
                        const locations = Array.isArray(data) ? data : (data.BusLocationList || []);
                        
                        locations.forEach(item => {
                            foundAny++;
                            let lat_raw = item.Position.Latitude;
                            let lon_raw = item.Position.Longitude;
                            // 測地系補正
                            let lat = lat_raw - 0.00010695 * lat_raw + 0.000017464 * lon_raw + 0.0046017;
                            let lon = lon_raw - 0.000046038 * lat_raw - 0.000083043 * lon_raw + 0.010040;
                            
                            if (markers[item.Bus.NumberPlate]) {
                                markers[item.Bus.NumberPlate].setLatLng([lat, lon]);
                            } else {
                                markers[item.Bus.NumberPlate] = L.circleMarker([lat, lon], {
                                    radius: 10, fillColor: t.name === '120番' ? '#ff4444' : '#00c851',
                                    color: "#fff", weight: 2, fillOpacity: 0.9
                                }).addTo(map).bindPopup(t.name + " (" + item.Bus.NumberPlate + ")");
                            }
                        });
                    } catch(e) { 
                        document.getElementById('debug').textContent = "エラー報告: ブラウザが通信を制限している可能性があります";
                    }
                }
                document.getElementById('info').textContent = "捕捉: " + foundAny + "台 (" + new Date().toLocaleTimeString() + ")";
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