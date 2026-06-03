from flask import Flask, request, jsonify
import json
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Dosya yolu (app.py ile aynı klasörde)
DOSYA_YOLU = os.path.join(os.path.dirname(__file__), 'turknetrinex.txt')

def verileri_yukle():
    try:
        with open(DOSYA_YOLU, 'r', encoding='utf-8') as f:
            icerik = f.read().strip()
        
        if not icerik:
            print("❌ Dosya boş!")
            return []
        
        # JSON'u yükle
        veri = json.loads(icerik)
        
        # Eğer gelen veri sözlük (dict) ise listeye çevir
        if isinstance(veri, dict):
            veritabani = [veri]
        elif isinstance(veri, list):
            veritabani = veri
        else:
            print("❌ Bilinmeyen format")
            return []
        
        print(f"✅ {len(veritabani)} kayıt başarıyla yüklendi!")
        return veritabani
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON hatası: {e}")
        return []
    except Exception as e:
        print(f"❌ Dosya okuma hatası: {e}")
        return []

# Veritabanını yükle
veritabani = verileri_yukle()

# Ana sayfa
@app.route('/')
def ana_sayfa():
    return jsonify({
        "api": "Turknet Müşteri Sorgu API",
        "durum": "Aktif",
        "kayit_sayisi": len(veritabani),
        "endpointler": {
            "ad_soyad_sorgu": "/sorgula?ad=BEYZANUR&soyad=KOSEOGLU",
            "tc_sorgu": "/sorgula?tc=10001763200",
            "hat_no_sorgu": "/sorgula?hatno=1780341975",
            "tum_veriler": "/tumveriler"
        }
    })

# Tüm verileri göster
@app.route('/tumveriler')
def tum_veriler():
    return jsonify({
        "toplam_kayit": len(veritabani),
        "veriler": veritabani
    })

# Ana sorgu endpoint'i (GET ile)
@app.route('/sorgula')
def sorgula():
    ad = request.args.get('ad', '').upper().strip()
    soyad = request.args.get('soyad', '').upper().strip()
    tc = request.args.get('tc', '').strip()
    hatno = request.args.get('hatno', '').strip()
    
    # Ad-soyad sorgusu
    if ad and soyad:
        sonuc = []
        for musteri in veritabani:
            musteri_ad = musteri.get('AD', '').upper()
            musteri_soyad = musteri.get('SOYAD', '').upper()
            if musteri_ad == ad and musteri_soyad == soyad:
                sonuc.append(musteri)
        
        if not sonuc:
            return jsonify({"bulunan": 0, "mesaj": f"{ad} {soyad} bulunamadı"})
        return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})
    
    # TC sorgusu
    elif tc:
        sonuc = [m for m in veritabani if m.get('TC_KIMLIK') == tc]
        if not sonuc:
            return jsonify({"bulunan": 0, "mesaj": f"TC {tc} bulunamadı"})
        return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})
    
    # Hat No sorgusu
    elif hatno:
        sonuc = [m for m in veritabani if m.get('HAT_NO') == hatno]
        if not sonuc:
            return jsonify({"bulunan": 0, "mesaj": f"Hat No {hatno} bulunamadı"})
        return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})
    
    else:
        return jsonify({
            "hata": "Geçersiz sorgu!",
            "ornek_kullanim": [
                "/sorgula?ad=BEYZANUR&soyad=KOSEOGLU",
                "/sorgula?tc=10001763200",
                "/sorgula?hatno=1780341975"
            ]
        }), 400

# POST metodları da ekleyelim (alternatif)
@app.route('/sorgu/adsoyad', methods=['POST'])
def sorgu_adsoyad_post():
    data = request.get_json()
    ad = data.get('ad', '').upper()
    soyad = data.get('soyad', '').upper()
    sonuc = [m for m in veritabani if m.get('AD', '').upper() == ad and m.get('SOYAD', '').upper() == soyad]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

@app.route('/sorgu/tc', methods=['POST'])
def sorgu_tc_post():
    data = request.get_json()
    tc = data.get('tc', '')
    sonuc = [m for m in veritabani if m.get('TC_KIMLIK') == tc]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

@app.route('/sorgu/hatno', methods=['POST'])
def sorgu_hatno_post():
    data = request.get_json()
    hatno = data.get('hatno', '')
    sonuc = [m for m in veritabani if m.get('HAT_NO') == hatno]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
