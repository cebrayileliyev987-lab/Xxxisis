from flask import Flask, request, jsonify
import json
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

veritabani = []
GITHUB_URL = "https://raw.githubusercontent.com/cebrayileliyev987-lab/Xxxisis/main/turknetrinex.txt"

def verileri_yukle():
    global veritabani
    try:
        response = requests.get(GITHUB_URL)
        satirlar = response.text.strip().split('\n')
        veritabani = []
        for satir in satirlar:
            try:
                veritabani.append(json.loads(satir))
            except:
                continue
        print(f"{len(veritabani)} kayıt yüklendi")
        return True
    except Exception as e:
        print(f"Hata: {e}")
        return False

@app.route('/')
def ana_sayfa():
    return jsonify({
        "api": "Turknet Müşteri Sorgu",
        "kullanim": {
            "GET_ornek": "/sorgula?ad=BEYZANUR&soyad=KOSEOGLU",
            "POST_ornek": "/sorgu/adsoyad - Body: {'ad':'BEYZANUR','soyad':'KOSEOGLU'}"
        }
    })

# ✅ YENİ! Tarayıcıdan direkt çalışan GET endpoint'i
@app.route('/sorgula', methods=['GET'])
def sorgula_get():
    ad = request.args.get('ad', '').upper()
    soyad = request.args.get('soyad', '').upper()
    tc = request.args.get('tc', '')
    hatno = request.args.get('hatno', '')
    
    if ad and soyad:
        sonuc = [m for m in veritabani 
                 if m.get('AD', '').upper() == ad 
                 and m.get('SOYAD', '').upper() == soyad]
        return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})
    
    elif tc:
        sonuc = [m for m in veritabani if m.get('TC_KIMLIK') == tc]
        return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})
    
    elif hatno:
        sonuc = [m for m in veritabani if m.get('HAT_NO') == hatno]
        return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})
    
    else:
        return jsonify({"hata": "Lütfen sorgu parametresi girin: ?ad=BEYZANUR&soyad=KOSEOGLU veya ?tc=10001763200 veya ?hatno=1780341975"})

@app.route('/sorgu/adsoyad', methods=['POST'])
def sorgu_adsoyad():
    data = request.get_json()
    ad = data.get('ad', '').upper()
    soyad = data.get('soyad', '').upper()
    sonuc = [m for m in veritabani 
             if m.get('AD', '').upper() == ad 
             and m.get('SOYAD', '').upper() == soyad]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

@app.route('/sorgu/tc', methods=['POST'])
def sorgu_tc():
    data = request.get_json()
    tc = data.get('tc', '')
    sonuc = [m for m in veritabani if m.get('TC_KIMLIK') == tc]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

@app.route('/sorgu/hatno', methods=['POST'])
def sorgu_hatno():
    data = request.get_json()
    hatno = data.get('hatno', '')
    sonuc = [m for m in veritabani if m.get('HAT_NO') == hatno]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

@app.route('/tumveriler', methods=['GET'])
def tum_veriler():
    return jsonify({"toplam": len(veritabani), "veriler": veritabani})

if __name__ == '__main__':
    verileri_yukle()
    app.run(host='0.0.0.0', port=10000)
