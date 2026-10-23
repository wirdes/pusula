# Çevrimdışı arama ölçümü

- Tarih: 2026-10-23
- Kart sayısı: 38 (hepsi taslak), soru sayısı: 214 (24 kapsam dışı)
- Kart metni: title, summary, keywords, steps
- Donanım: PC işlemcisi (CPU), sorgular tek tek kodlandı. Süreler telefonda farklı olur, yalnızca modelleri kıyaslamak içindir.

## Genel sonuç

| Model | Parametre (M) | hit@1 | hit@3 | MRR | Kapsam dışı AUROC | Sorgu süresi (ms) |
|---|---|---|---|---|---|---|
| modernbert-tr-embed | 149 | 85 | 97 | 91 | 0.94 | 43.3 |
| bge-m3 | 568 | 83 | 94 | 89 | 0.91 | 70.7 |
| bm25-f5 | – | 84 | 92 | 89 | 0.86 | 0.0 |
| bm25 | – | 75 | 87 | 82 | 0.80 | 0.0 |
| bert-turkish-nli-stsb | 111 | 70 | 87 | 80 | 0.91 | 18.8 |
| e5-small | 118 | 68 | 87 | 78 | 0.81 | 8.7 |
| static-mrl-multilingual | 108 | 59 | 81 | 72 | 0.81 | 0.3 |
| minilm-l12-multilingual | 118 | 57 | 75 | 68 | 0.89 | 8.3 |

hit@1: doğru kart ilk sırada (%). hit@3: ilk üçte (%). MRR: ortalama ters sıra (%). AUROC: kapsam dışı soruları en yüksek benzerlik skoruna bakarak ayırabilme (0,5 rastgele, 1,0 kusursuz).

## Soru tipine göre hit@1 (%)

| Model | resmi | gunluk | diakritiksiz | yazim_hatasi | panik | dolayli | ses |
|---|---|---|---|---|---|---|---|
| modernbert-tr-embed | 97 | 84 | 84 | 83 | 60 | 85 | 70 |
| bge-m3 | 100 | 89 | 84 | 89 | 30 | 79 | 40 |
| bm25-f5 | 84 | 89 | 89 | 78 | 90 | 79 | 60 |
| bm25 | 66 | 74 | 89 | 72 | 80 | 79 | 50 |
| bert-turkish-nli-stsb | 89 | 82 | 68 | 61 | 20 | 67 | 40 |
| e5-small | 92 | 66 | 62 | 83 | 50 | 59 | 40 |
| static-mrl-multilingual | 61 | 71 | 57 | 67 | 40 | 51 | 60 |
| minilm-l12-multilingual | 74 | 66 | 49 | 61 | 10 | 56 | 40 |

## En iyi modelin (modernbert-tr-embed) ilk sırada bulamadığı sorular

| Soru | Tip | Beklenen | Bulunan ilk kart |
|---|---|---|---|
| köprünün üstündeyken her şey sallanmaya başladı | dolayli | deprem-ani-aracta | deprem-ani-disarida |
| sallantı durdu şimdi ne yapıcaz | gunluk | deprem-sonrasi-ilk-adimlar | deprem-ani-bina-ici |
| enkazın altnda kaldm ne yapcam | yazim_hatasi | enkaz-altinda-kalma | enkazdaki-birine-yardim |
| babam yere dustu nefes almiyor ne yapayim | diakritiksiz | temel-yasam-destegi | bilinci-kapali-nefes-aliyor |
| arkadaşım bayıldı uyandıramıyoruz nefes de almıyor gibi | ses | temel-yasam-destegi | bilinci-kapali-nefes-aliyor |
| enkazdan çıkardık iyi görünüyo hastaneye götürmesek olur mu | gunluk | ezilme-yaralanmasi | enkazdaki-birine-yardim |
| yüksekten düştü bacaklarını hissetmiyor | dolayli | bas-ve-omurga-yaralanmasi | kirik-ve-cikik |
| kafasını çarptı kusuyo | gunluk | bas-ve-omurga-yaralanmasi | havayolu-tikanmasi |
| kaza geçirdi sapsarı oldu bilinci gidip geliyo | gunluk | sok | bas-ve-omurga-yaralanmasi |
| boğuluyor | panik | havayolu-tikanmasi | enkaz-altinda-kalma |
| her yer duman cikamiyorum | diakritiksiz | yangin | enkaz-altinda-kalma |
| YANGIN VAR | panik | yangin | orman-yangininda-kacis |
| telefonda sadece acil çağrı yazıyor | dolayli | telefon-pili-ve-sebeke | yardim-isareti-verme |
| geceleyin dağda mahsur kaldık fenerimiz var | dolayli | yardim-isareti-verme | dogada-kaybolma |
| nefes alamiyorum gibi hissediyorum cok korkuyorum | diakritiksiz | panik-ve-psikolojik-ilk-yardim | bilinci-kapali-nefes-aliyor |
| arkadaşım deprem sonrası konuşmuyor boş boş bakıyor ne yapabilirim | ses | panik-ve-psikolojik-ilk-yardim | deprem-sonrasi-ilk-adimlar |
| dagda yolumuzu sasirdik hava kariyor | diakritiksiz | dogada-kaybolma | kar-firtinasinda-aracta-mahsur |
| yere yatınca soğuk içimize işliyor | dolayli | barinak-ve-soguktan-korunma | hipotermi |
| suyumuz bitti etrafta dere falan yok | gunluk | su-bulma | sel-ve-su-baskini |
| deniz suyu içilirmi susadk | yazim_hatasi | su-bulma | su-aritma |
| akrep iğnesini batırdı ayağı şişiyo | gunluk | yilan-ve-akrep-sokmasi | ari-sokmasi-ve-alerjik-reaksiyon |
| YILAN | panik | yilan-ve-akrep-sokmasi | yardim-isareti-verme |
| sicaktan basi donuyor kusuyor | diakritiksiz | sicak-carpmasi | hipotermi |
| öğlen güneşinde yürüdük şimdi saçma sapan konuşuyor cildi kıpkırmızı | dolayli | sicak-carpmasi | hipotermi |
| dedem sıcakta dışarıda kaldı çok halsiz terlemiyor bile | ses | sicak-carpmasi | hipotermi |
| Gök gürültülü fırtınada açık arazideysem ne yapmalıyım? | resmi | yildirim-ve-firtina | deprem-ani-disarida |
| yildirim carpan birine dokunulur mu | diakritiksiz | yildirim-ve-firtina | havayolu-tikanmasi |
| fırtnada çadırda kalmak güvenlimi | yazim_hatasi | yildirim-ve-firtina | deprem-ani-disarida |
| AĞAÇLAR YANIYOR | panik | orman-yangininda-kacis | ates-yakma |
