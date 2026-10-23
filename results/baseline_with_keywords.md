# Çevrimdışı arama ölçümü

- Tarih: 2026-10-23
- Kart sayısı: 38 (hepsi taslak), soru sayısı: 214 (24 kapsam dışı)
- Karar akışları: 3
- Kart metni: title, summary, keywords, steps
- Donanım: PC işlemcisi (CPU), sorgular tek tek kodlandı. Süreler telefonda farklı olur, yalnızca modelleri kıyaslamak içindir.

## Genel sonuç

| Model | Parametre (M) | hit@1 | hit@3 | MRR | Kapsam dışı AUROC | Soru sorulan (%) | Akışla düzelen | Sorgu süresi (ms) |
|---|---|---|---|---|---|---|---|---|
| modernbert-tr-embed | 149 | 88 | 97 | 93 | 0.94 | 21 | 7 | 42.6 |
| bge-m3 | 568 | 86 | 95 | 91 | 0.91 | 22 | 7 | 73.7 |
| bm25-f5 | – | 84 | 93 | 89 | 0.85 | 19 | 2 | 0.0 |
| bm25 | – | 75 | 88 | 82 | 0.79 | 24 | 3 | 0.0 |
| bert-turkish-nli-stsb | 111 | 72 | 88 | 81 | 0.91 | 23 | 5 | 19.7 |
| e5-small | 118 | 72 | 88 | 80 | 0.81 | 24 | 6 | 8.7 |
| static-mrl-multilingual | 108 | 62 | 82 | 73 | 0.81 | 22 | 6 | 0.2 |
| minilm-l12-multilingual | 118 | 62 | 78 | 72 | 0.89 | 23 | 8 | 8.5 |

hit@1: doğru kart ya da doğru karta götüren akış ilk sırada (%). hit@3: ilk üçte (%). MRR: ortalama ters sıra (%). AUROC: kapsam dışı soruları en yüksek benzerlik skoruna bakarak ayırabilme (0,5 rastgele, 1,0 kusursuz). Soru sorulan: kapsam içi soruların kaçında kullanıcıya akış sorusu soruluyor. Akışla düzelen: yalnızca kartlara bakılsaydı yanlış kart çıkacakken akışın sorusuyla doğru karta ulaşılan soru sayısı.

## Soru tipine göre hit@1 (%)

| Model | resmi | gunluk | diakritiksiz | yazim_hatasi | panik | dolayli | ses |
|---|---|---|---|---|---|---|---|
| modernbert-tr-embed | 97 | 87 | 89 | 89 | 60 | 87 | 90 |
| bge-m3 | 100 | 92 | 86 | 89 | 50 | 82 | 60 |
| bm25-f5 | 82 | 87 | 92 | 83 | 90 | 79 | 60 |
| bm25 | 63 | 76 | 89 | 72 | 80 | 77 | 50 |
| bert-turkish-nli-stsb | 87 | 82 | 68 | 67 | 30 | 69 | 60 |
| e5-small | 92 | 71 | 62 | 83 | 70 | 59 | 60 |
| static-mrl-multilingual | 61 | 74 | 54 | 67 | 60 | 54 | 70 |
| minilm-l12-multilingual | 79 | 68 | 54 | 61 | 20 | 56 | 60 |

## En iyi modelin (modernbert-tr-embed) ilk sırada bulamadığı sorular

| Soru | Tip | Beklenen | Bulunan ilk kart ya da akış |
|---|---|---|---|
| köprünün üstündeyken her şey sallanmaya başladı | dolayli | deprem-ani-aracta | deprem-ani-disarida |
| sallantı durdu şimdi ne yapıcaz | gunluk | deprem-sonrasi-ilk-adimlar | deprem-ani-bina-ici |
| yüksekten düştü bacaklarını hissetmiyor | dolayli | bas-ve-omurga-yaralanmasi | kirik-ve-cikik |
| kafasını çarptı kusuyo | gunluk | bas-ve-omurga-yaralanmasi | havayolu-tikanmasi |
| kaza geçirdi sapsarı oldu bilinci gidip geliyo | gunluk | sok | bas-ve-omurga-yaralanmasi |
| boğuluyor | panik | havayolu-tikanmasi | enkaz-durumu |
| her yer duman cikamiyorum | diakritiksiz | yangin | enkaz-durumu |
| YANGIN VAR | panik | yangin | orman-yangininda-kacis |
| telefonda sadece acil çağrı yazıyor | dolayli | telefon-pili-ve-sebeke | yardim-isareti-verme |
| geceleyin dağda mahsur kaldık fenerimiz var | dolayli | yardim-isareti-verme | dogada-kaybolma |
| nefes alamiyorum gibi hissediyorum cok korkuyorum | diakritiksiz | panik-ve-psikolojik-ilk-yardim | bilinc-ve-nefes |
| arkadaşım deprem sonrası konuşmuyor boş boş bakıyor ne yapabilirim | ses | panik-ve-psikolojik-ilk-yardim | deprem-sonrasi-ilk-adimlar |
| dagda yolumuzu sasirdik hava kariyor | diakritiksiz | dogada-kaybolma | kar-firtinasinda-aracta-mahsur |
| yere yatınca soğuk içimize işliyor | dolayli | barinak-ve-soguktan-korunma | vucut-isisi |
| suyumuz bitti etrafta dere falan yok | gunluk | su-bulma | sel-ve-su-baskini |
| deniz suyu içilirmi susadk | yazim_hatasi | su-bulma | su-aritma |
| akrep iğnesini batırdı ayağı şişiyo | gunluk | yilan-ve-akrep-sokmasi | ari-sokmasi-ve-alerjik-reaksiyon |
| YILAN | panik | yilan-ve-akrep-sokmasi | yardim-isareti-verme |
| Gök gürültülü fırtınada açık arazideysem ne yapmalıyım? | resmi | yildirim-ve-firtina | deprem-ani-disarida |
| yildirim carpan birine dokunulur mu | diakritiksiz | yildirim-ve-firtina | havayolu-tikanmasi |
| fırtnada çadırda kalmak güvenlimi | yazim_hatasi | yildirim-ve-firtina | deprem-ani-disarida |
| AĞAÇLAR YANIYOR | panik | orman-yangininda-kacis | ates-yakma |
