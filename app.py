from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

JSON_PATH = os.path.join(os.path.dirname(__file__), 'turknetrinex.json')

def json_yukle():
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            icerik = f.read().strip()
        
        # JSON'u yükle (alt alta olabilir)
        veri = json.loads(icerik)
        
        # Dict ise listeye çevir
        if isinstance(veri, dict):
            return [veri]
        elif isinstance(veri, list):
            return veri
        else:
            return []
            
    except FileNotFoundError:
        print(f"❌ Dosya bulunamadı: {JSON_PATH}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON hatası: {e}")
        return []

# Veritabanını yükle
VERITABANI = json_yukle()
print(f"✅ {len(VERITABANI)} kayıt yüklendi!")

@app.route('/')
def home():
    return jsonify({
        "status": "API Calisiyor",
        "kayit_sayisi": len(VERITABANI),
        "endpoints": {
            "/tumveriler": "Tüm verileri getir",
            "/sorgula?ad=X&soyad=Y": "Ad soyad ile sorgula (tüm veriyi getirir)",
            "/sorgula?tc=X": "TC ile sorgula (tüm veriyi getirir)",
            "/sorgula?hatno=X": "Hat no ile sorgula (tüm veriyi getirir)"
        }
    })

@app.route('/tumveriler')
def tumveriler():
    """Tüm verileri olduğu gibi gösterir"""
    if not VERITABANI:
        return jsonify({"hata": "Veritabanı boş"}), 503
    
    # Veriyi olduğu gibi gönder (eksiksiz)
    if len(VERITABANI) == 1:
        return jsonify(VERITABANI[0])
    else:
        return jsonify(VERITABANI)

@app.route('/sorgula')
def sorgula():
    """Sorgu yapar ve eşleşen KAYDIN TAMAMINI gönderir"""
    ad = request.args.get('ad', '').upper()
    soyad = request.args.get('soyad', '').upper()
    tc = request.args.get('tc', '')
    hatno = request.args.get('hatno', '')
    
    if not VERITABANI:
        return jsonify({"hata": "Veritabanı boş"}), 503
    
    # Her kayıtta arama yap
    for kayit in VERITABANI:
        if ad and soyad:
            # Ad ve soyad eşleşmesi
            if kayit.get('AD', '').upper() == ad and kayit.get('SOYAD', '').upper() == soyad:
                return jsonify(kayit)  # TÜM VERİYİ GÖNDER
        elif tc:
            # TC eşleşmesi
            if kayit.get('TC_KIMLIK') == tc:
                return jsonify(kayit)  # TÜM VERİYİ GÖNDER
        elif hatno:
            # Hat no eşleşmesi
            if kayit.get('HAT_NO') == hatno:
                return jsonify(kayit)  # TÜM VERİYİ GÖNDER
    
    return jsonify({"hata": "Kayıt bulunamadı"}), 404

@app.route('/sorgu/adsoyad', methods=['POST'])
def sorgu_adsoyad():
    """POST ile ad soyad sorgusu - TÜM VERİYİ GÖNDER"""
    data = request.get_json()
    if not data:
        return jsonify({"hata": "JSON body gerekli"}), 400
    
    ad = data.get('ad', '').upper()
    soyad = data.get('soyad', '').upper()
    
    for kayit in VERITABANI:
        if kayit.get('AD', '').upper() == ad and kayit.get('SOYAD', '').upper() == soyad:
            return jsonify(kayit)  # TÜM VERİYİ GÖNDER
    
    return jsonify({"hata": "Kayıt bulunamadı"}), 404

@app.route('/sorgu/tc', methods=['POST'])
def sorgu_tc():
    """POST ile TC sorgusu - TÜM VERİYİ GÖNDER"""
    data = request.get_json()
    if not data:
        return jsonify({"hata": "JSON body gerekli"}), 400
    
    tc = data.get('tc', '')
    
    for kayit in VERITABANI:
        if kayit.get('TC_KIMLIK') == tc:
            return jsonify(kayit)  # TÜM VERİYİ GÖNDER
    
    return jsonify({"hata": "Kayıt bulunamadı"}), 404

@app.route('/sorgu/hatno', methods=['POST'])
def sorgu_hatno():
    """POST ile hat no sorgusu - TÜM VERİYİ GÖNDER"""
    data = request.get_json()
    if not data:
        return jsonify({"hata": "JSON body gerekli"}), 400
    
    hatno = data.get('hatno', '')
    
    for kayit in VERITABANI:
        if kayit.get('HAT_NO') == hatno:
            return jsonify(kayit)  # TÜM VERİYİ GÖNDER
    
    return jsonify({"hata": "Kayıt bulunamadı"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
