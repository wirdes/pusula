# Çevrimdışı arama ölçümü

- Tarih: 2026-10-23
- Kart sayısı: 24 (hepsi taslak), soru sayısı: 136 (16 kapsam dışı)
- Kart metni: title, summary, steps
- Donanım: PC işlemcisi (CPU), sorgular tek tek kodlandı. Süreler telefonda farklı olur, yalnızca modelleri kıyaslamak içindir.

## Genel sonuç

| Model | Parametre (M) | hit@1 | hit@3 | MRR | Kapsam dışı AUROC | Sorgu süresi (ms) |
|---|---|---|---|---|---|---|
| modernbert-tr-embed | 149 | 75 | 95 | 85 | 0.95 | 39.8 |
| bge-m3 | 568 | 72 | 91 | 82 | 0.90 | 71.9 |
| e5-small | 118 | 61 | 79 | 70 | 0.82 | 9.3 |
| bert-turkish-nli-stsb | 111 | 55 | 74 | 67 | 0.93 | 20.2 |
| minilm-l12-multilingual | 118 | 52 | 75 | 66 | 0.89 | 8.8 |
| bm25-f5 | – | 52 | 72 | 64 | 0.78 | 0.0 |
| static-mrl-multilingual | 108 | 42 | 59 | 54 | 0.73 | 0.3 |
| bm25 | – | 42 | 62 | 53 | 0.67 | 0.0 |

hit@1: doğru kart ilk sırada (%). hit@3: ilk üçte (%). MRR: ortalama ters sıra (%). AUROC: kapsam dışı soruları en yüksek benzerlik skoruna bakarak ayırabilme (0,5 rastgele, 1,0 kusursuz).

## Soru tipine göre hit@1 (%)

| Model | resmi | gunluk | diakritiksiz | yazim_hatasi | panik | dolayli | ses |
|---|---|---|---|---|---|---|---|
| modernbert-tr-embed | 96 | 79 | 70 | 83 | 57 | 60 | 60 |
| bge-m3 | 88 | 79 | 61 | 100 | 29 | 60 | 60 |
| e5-small | 88 | 58 | 52 | 75 | 57 | 44 | 40 |
| bert-turkish-nli-stsb | 71 | 54 | 57 | 67 | 0 | 52 | 40 |
| minilm-l12-multilingual | 67 | 67 | 43 | 67 | 0 | 44 | 40 |
| bm25-f5 | 50 | 54 | 48 | 67 | 57 | 52 | 20 |
| static-mrl-multilingual | 54 | 46 | 39 | 33 | 43 | 36 | 40 |
| bm25 | 54 | 38 | 43 | 42 | 29 | 40 | 20 |

## En iyi modelin (modernbert-tr-embed) ilk sırada bulamadığı sorular

| Soru | Tip | Beklenen | Bulunan ilk kart |
|---|---|---|---|
| deprem oluyor ofisteyim ne yapmaliyim | diakritiksiz | deprem-ani-bina-ici | deprem-sonrasi-ilk-adimlar |
| köprünün üstündeyken her şey sallanmaya başladı | dolayli | deprem-ani-aracta | deprem-ani-disarida |
| sallantı durdu şimdi ne yapıcaz | gunluk | deprem-sonrasi-ilk-adimlar | deprem-ani-bina-ici |
| Enkaz altında kaldım, ne yapmalıyım? | resmi | enkaz-altinda-kalma | enkazdaki-birine-yardim |
| sıkıştım çıkamıyorum | panik | enkaz-altinda-kalma | enkazdaki-birine-yardim |
| enkazın altnda kaldm ne yapcam | yazim_hatasi | enkaz-altinda-kalma | enkazdaki-birine-yardim |
| koluna demir saplandı çıkarayım mı | dolayli | ciddi-kanama | kirik-ve-cikik |
| nefes almıyor | panik | temel-yasam-destegi | bilinci-kapali-nefes-aliyor |
| babam yere dustu nefes almiyor ne yapayim | diakritiksiz | temel-yasam-destegi | bilinci-kapali-nefes-aliyor |
| arkadaşım bayıldı uyandıramıyoruz nefes de almıyor gibi | ses | temel-yasam-destegi | bilinci-kapali-nefes-aliyor |
| annem baygın kolonya koklatalım mı | dolayli | bilinci-kapali-nefes-aliyor | havayolu-tikanmasi |
| koma pozisyonu nasl verilr | yazim_hatasi | bilinci-kapali-nefes-aliyor | ciddi-kanama |
| enkazdan çıkardık iyi görünüyo hastaneye götürmesek olur mu | gunluk | ezilme-yaralanmasi | enkazdaki-birine-yardim |
| kolu kırıldı galiba çok şişti | gunluk | kirik-ve-cikik | ezilme-yaralanmasi |
| düştükten sonra bileğini oynatamıyor aşırı ağrıyor | dolayli | kirik-ve-cikik | ezilme-yaralanmasi |
| yüksekten düştü bacaklarını hissetmiyor | dolayli | bas-ve-omurga-yaralanmasi | ezilme-yaralanmasi |
| kafasını çarptı kusuyo | gunluk | bas-ve-omurga-yaralanmasi | havayolu-tikanmasi |
| kulağından kan geliyor başına beton düştü | dolayli | bas-ve-omurga-yaralanmasi | enkaz-altinda-kalma |
| yanik var dis macunu surelim mi | diakritiksiz | yanik | havayolu-tikanmasi |
| sobanın üstüne düştü kolu kızardı su topladı | dolayli | yanik | hipotermi |
| yaralı soğuk soğuk terliyor rengi bembeyaz nabzı çok hızlı | dolayli | sok | hipotermi |
| kan kaybetti rengi soldu titriyor | diakritiksiz | sok, ciddi-kanama | hipotermi |
| kaza geçirdi sapsarı oldu bilinci gidip geliyo | gunluk | sok | bas-ve-omurga-yaralanmasi |
| boğuluyor | panik | havayolu-tikanmasi | enkaz-altinda-kalma |
| heimlich manevrasi nasil yapilir | diakritiksiz | havayolu-tikanmasi | yardim-isareti-verme |
| binaya girince çürük yumurta gibi bir koku aldım | dolayli | gaz-kacagi | deprem-sonrasi-ilk-adimlar |
| her yer duman cikamiyorum | diakritiksiz | yangin | gaz-kacagi |
| telefonda sadece acil çağrı yazıyor | dolayli | telefon-pili-ve-sebeke | yardim-isareti-verme |
| nefes alamiyorum gibi hissediyorum cok korkuyorum | diakritiksiz | panik-ve-psikolojik-ilk-yardim | bilinci-kapali-nefes-aliyor |
| arkadaşım deprem sonrası konuşmuyor boş boş bakıyor ne yapabilirim | ses | panik-ve-psikolojik-ilk-yardim | deprem-sonrasi-ilk-adimlar |
