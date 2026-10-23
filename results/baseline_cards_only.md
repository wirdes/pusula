# Çevrimdışı arama ölçümü

- Tarih: 2026-10-23
- Kart sayısı: 38 (hepsi taslak), soru sayısı: 214 (24 kapsam dışı)
- Karar akışları: kullanılmadı (yalnızca kartlar)
- Kart metni: title, summary, steps
- Donanım: PC işlemcisi (CPU), sorgular tek tek kodlandı. Süreler telefonda farklı olur, yalnızca modelleri kıyaslamak içindir.

## Genel sonuç

| Model | Parametre (M) | hit@1 | hit@3 | MRR | Kapsam dışı AUROC | Soru sorulan (%) | Akışla düzelen | Sorgu süresi (ms) |
|---|---|---|---|---|---|---|---|---|
| modernbert-tr-embed | 149 | 75 | 95 | 85 | 0.93 | 0 | 0 | 42.9 |
| bge-m3 | 568 | 69 | 92 | 80 | 0.88 | 0 | 0 | 72.4 |
| e5-small | 118 | 61 | 76 | 70 | 0.76 | 0 | 0 | 9.1 |
| bm25-f5 | – | 57 | 70 | 65 | 0.73 | 0 | 0 | 0.0 |
| bert-turkish-nli-stsb | 111 | 51 | 73 | 65 | 0.91 | 0 | 0 | 20.3 |
| minilm-l12-multilingual | 118 | 49 | 71 | 62 | 0.88 | 0 | 0 | 8.8 |
| bm25 | – | 46 | 56 | 53 | 0.68 | 0 | 0 | 0.0 |
| static-mrl-multilingual | 108 | 38 | 56 | 50 | 0.73 | 0 | 0 | 0.3 |

hit@1: doğru kart ya da doğru karta götüren akış ilk sırada (%). hit@3: ilk üçte (%). MRR: ortalama ters sıra (%). AUROC: kapsam dışı soruları en yüksek benzerlik skoruna bakarak ayırabilme (0,5 rastgele, 1,0 kusursuz). Soru sorulan: kapsam içi soruların kaçında kullanıcıya akış sorusu soruluyor. Akışla düzelen: yalnızca kartlara bakılsaydı yanlış kart çıkacakken akışın sorusuyla doğru karta ulaşılan soru sayısı.

## Soru tipine göre hit@1 (%)

| Model | resmi | gunluk | diakritiksiz | yazim_hatasi | panik | dolayli | ses |
|---|---|---|---|---|---|---|---|
| modernbert-tr-embed | 95 | 82 | 70 | 78 | 40 | 67 | 60 |
| bge-m3 | 92 | 71 | 70 | 89 | 30 | 54 | 40 |
| e5-small | 89 | 53 | 57 | 78 | 40 | 44 | 60 |
| bm25-f5 | 76 | 42 | 62 | 67 | 70 | 49 | 30 |
| bert-turkish-nli-stsb | 79 | 45 | 54 | 56 | 10 | 41 | 20 |
| minilm-l12-multilingual | 63 | 58 | 41 | 61 | 0 | 46 | 40 |
| bm25 | 66 | 29 | 57 | 50 | 30 | 44 | 10 |
| static-mrl-multilingual | 50 | 34 | 43 | 50 | 30 | 23 | 40 |

## En iyi modelin (modernbert-tr-embed) ilk sırada bulamadığı sorular

| Soru | Tip | Beklenen | Bulunan ilk kart ya da akış |
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
| her yer duman cikamiyorum | diakritiksiz | yangin | orman-yangininda-kacis |
| YANGIN VAR | panik | yangin | orman-yangininda-kacis |
| telefonda sadece acil çağrı yazıyor | dolayli | telefon-pili-ve-sebeke | yardim-isareti-verme |
| geceleyin dağda mahsur kaldık fenerimiz var | dolayli | yardim-isareti-verme | dogada-kaybolma |
| nefes alamiyorum gibi hissediyorum cok korkuyorum | diakritiksiz | panik-ve-psikolojik-ilk-yardim | bilinci-kapali-nefes-aliyor |
| arkadaşım deprem sonrası konuşmuyor boş boş bakıyor ne yapabilirim | ses | panik-ve-psikolojik-ilk-yardim | deprem-sonrasi-ilk-adimlar |
| dagda yolumuzu sasirdik hava kariyor | diakritiksiz | dogada-kaybolma | kar-firtinasinda-aracta-mahsur |
| kamptaki atesi nasil tam olarak sonduruz | diakritiksiz | ates-yakma | yangin |
| yere yatınca soğuk içimize işliyor | dolayli | barinak-ve-soguktan-korunma | hipotermi |
| dağda kaldık hava kararıyor üstümüzü örtecek bir şey yok | ses | barinak-ve-soguktan-korunma | kar-firtinasinda-aracta-mahsur |
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
