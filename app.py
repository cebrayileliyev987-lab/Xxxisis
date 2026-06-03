from flask import Flask, request, jsonify
import json
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Tüm domainlerden gelen isteklere izin verir

# --- VERİ YÜKLEME (GitHub RAW linki ile) ---
GITHUB_URL = "https://raw.githubusercontent.com/cebrayileliyev987-lab/Xxxisis/main/turknetrinex.txt"
veritabani = []

def verileri_yukle():
    global veritabani
    try:
        response = requests.get(GITHUB_URL)
        response.raise_for_status() # HTTP hatası varsa fırlat
        satirlar = response.text.strip().split('\n')
        veritabani = []
        for satir in satirlar:
            if satir.strip(): # Boş satırları atla
                try:
                    veritabani.append(json.loads(satir))
                except json.JSONDecodeError:
                    print(f"JSON ayrıştırma hatası: {satir[:100]}...")
                    continue
        print(f"✅ {len(veritabani)} kayıt başarıyla yüklendi.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ GitHub'dan veri çekilemedi: {e}")
        return False
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        return False

# Ana sayfa
@app.route('/')
def ana_sayfa():
    return jsonify({
        "api": "Turknet Müşteri Sorgu",
        "endpoints": {
            "/sorgu/adsoyad": "POST - {'ad': 'BEYZANUR', 'soyad': 'KOSEOGLU'}",
            "/sorgu/tc": "POST - {'tc': '10001763200'}",
            "/sorgu/hatno": "POST - {'hatno': '1780341975'}",
            "/sorgula": "GET - ?ad=BEYZANUR&soyad=KOSEOGLU veya ?tc=... veya ?hatno=..."
        }
    })

# Tüm veriler (GET)
@app.route('/tumveriler', methods=['GET'])
def tum_veriler():
    return jsonify({"toplam": len(veritabani), "veriler": veritabani})

# --- SORGU ENDPOINT'LERİ ---

# 1. GET ile sorgulama (Tarayıcıdan kullanım için)
@app.route('/sorgula', methods=['GET'])
def sorgula_get():
    ad = request.args.get('ad', '').upper().strip()
    soyad = request.args.get('soyad', '').upper().strip()
    tc = request.args.get('tc', '').strip()
    hatno = request.args.get('hatno', '').strip()

    if ad and soyad:
        sonuc = [m for m in veritabani if m.get('AD', '').upper() == ad and m.get('SOYAD', '').upper() == soyad]
        return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})
    elif tc:
        sonuc = [m for m in veritabani if m.get('TC_KIMLIK') == tc]
        return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})
    elif hatno:
        sonuc = [m for m in veritabani if m.get('HAT_NO') == hatno]
        return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})
    else:
        return jsonify({"hata": "Lütfen geçerli bir sorgu parametresi girin. Örn: ?ad=BEYZANUR&soyad=KOSEOGLU"}), 400

# 2. POST ile sorgulama (API standardı)
@app.route('/sorgu/adsoyad', methods=['POST'])
def sorgu_adsoyad():
    data = request.get_json()
    if not data: return jsonify({"hata": "JSON body gerekli"}), 400
    ad = data.get('ad', '').upper()
    soyad = data.get('soyad', '').upper()
    if not ad or not soyad: return jsonify({"hata": "ad ve soyad alanları gerekli"}), 400
    sonuc = [m for m in veritabani if m.get('AD', '').upper() == ad and m.get('SOYAD', '').upper() == soyad]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

@app.route('/sorgu/tc', methods=['POST'])
def sorgu_tc():
    data = request.get_json()
    if not data: return jsonify({"hata": "JSON body gerekli"}), 400
    tc = data.get('tc', '')
    if not tc: return jsonify({"hata": "tc alanı gerekli"}), 400
    sonuc = [m for m in veritabani if m.get('TC_KIMLIK') == tc]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

@app.route('/sorgu/hatno', methods=['POST'])
def sorgu_hatno():
    data = request.get_json()
    if not data: return jsonify({"hata": "JSON body gerekli"}), 400
    hatno = data.get('hatno', '')
    if not hatno: return jsonify({"hata": "hatno alanı gerekli"}), 400
    sonuc = [m for m in veritabani if m.get('HAT_NO') == hatno]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

# --- UYGULAMA BAŞLATMA (Render için kritik) ---
if __name__ != '__main__':
    # Bu blok, gunicorn ile çalışırken verilerin yüklenmesini sağlar
    verileri_yukle()
else:
    # Bu blok, localde python app.py ile çalıştırırken
    verileri_yukle()
    app.run(host='0.0.0.0', port=10000, debug=False)
