# Çevrimdışı arama ölçümü

- Tarih: 2026-10-23
- Kart sayısı: 38 (hepsi taslak), soru sayısı: 214 (24 kapsam dışı)
- Karar akışları: 3
- Kart metni: title, summary, steps
- Donanım: PC işlemcisi (CPU), sorgular tek tek kodlandı. Süreler telefonda farklı olur, yalnızca modelleri kıyaslamak içindir.

## Genel sonuç

| Model | Parametre (M) | hit@1 | hit@3 | MRR | Kapsam dışı AUROC | Soru sorulan (%) | Akışla düzelen | Sorgu süresi (ms) |
|---|---|---|---|---|---|---|---|---|
| modernbert-tr-embed | 149 | 81 | 95 | 88 | 0.93 | 23 | 10 | 41.4 |
| pusula-student | 118 | 77 | 88 | 84 | 0.77 | 19 | 8 | 8.8 |
| bge-m3 | 568 | 74 | 93 | 83 | 0.89 | 25 | 10 | 71.3 |
| e5-small | 118 | 65 | 81 | 73 | 0.77 | 23 | 8 | 8.9 |

hit@1: doğru kart ya da doğru karta götüren akış ilk sırada (%). hit@3: ilk üçte (%). MRR: ortalama ters sıra (%). AUROC: kapsam dışı soruları en yüksek benzerlik skoruna bakarak ayırabilme (0,5 rastgele, 1,0 kusursuz). Soru sorulan: kapsam içi soruların kaçında kullanıcıya akış sorusu soruluyor. Akışla düzelen: yalnızca kartlara bakılsaydı yanlış kart çıkacakken akışın sorusuyla doğru karta ulaşılan soru sayısı.

## Soru tipine göre hit@1 (%)

| Model | resmi | gunluk | diakritiksiz | yazim_hatasi | panik | dolayli | ses |
|---|---|---|---|---|---|---|---|
| modernbert-tr-embed | 97 | 84 | 76 | 83 | 60 | 69 | 80 |
| pusula-student | 95 | 76 | 81 | 67 | 70 | 64 | 80 |
| bge-m3 | 95 | 74 | 76 | 89 | 50 | 56 | 60 |
| e5-small | 92 | 63 | 59 | 72 | 50 | 44 | 70 |

## En iyi modelin (modernbert-tr-embed) ilk sırada bulamadığı sorular

| Soru | Tip | Beklenen | Bulunan ilk kart ya da akış |
|---|---|---|---|
| deprem oluyor ofisteyim ne yapmaliyim | diakritiksiz | deprem-ani-bina-ici | deprem-sonrasi-ilk-adimlar |
| köprünün üstündeyken her şey sallanmaya başladı | dolayli | deprem-ani-aracta | deprem-ani-disarida |
| sallantı durdu şimdi ne yapıcaz | gunluk | deprem-sonrasi-ilk-adimlar | deprem-ani-bina-ici |
| koluna demir saplandı çıkarayım mı | dolayli | ciddi-kanama | kirik-ve-cikik |
| annem baygın kolonya koklatalım mı | dolayli | bilinci-kapali-nefes-aliyor | havayolu-tikanmasi |
| koma pozisyonu nasl verilr | yazim_hatasi | bilinci-kapali-nefes-aliyor | ciddi-kanama |
| kolu kırıldı galiba çok şişti | gunluk | kirik-ve-cikik | enkaz-durumu |
| düştükten sonra bileğini oynatamıyor aşırı ağrıyor | dolayli | kirik-ve-cikik | enkaz-durumu |
| yüksekten düştü bacaklarını hissetmiyor | dolayli | bas-ve-omurga-yaralanmasi | enkaz-durumu |
| kafasını çarptı kusuyo | gunluk | bas-ve-omurga-yaralanmasi | havayolu-tikanmasi |
| kulağından kan geliyor başına beton düştü | dolayli | bas-ve-omurga-yaralanmasi | enkaz-durumu |
| yanik var dis macunu surelim mi | diakritiksiz | yanik | havayolu-tikanmasi |
| sobanın üstüne düştü kolu kızardı su topladı | dolayli | yanik | vucut-isisi |
| yaralı soğuk soğuk terliyor rengi bembeyaz nabzı çok hızlı | dolayli | sok | vucut-isisi |
| kan kaybetti rengi soldu titriyor | diakritiksiz | sok, ciddi-kanama | vucut-isisi |
| kaza geçirdi sapsarı oldu bilinci gidip geliyo | gunluk | sok | bas-ve-omurga-yaralanmasi |
| boğuluyor | panik | havayolu-tikanmasi | enkaz-durumu |
| heimlich manevrasi nasil yapilir | diakritiksiz | havayolu-tikanmasi | yardim-isareti-verme |
| binaya girince çürük yumurta gibi bir koku aldım | dolayli | gaz-kacagi | deprem-sonrasi-ilk-adimlar |
| her yer duman cikamiyorum | diakritiksiz | yangin | orman-yangininda-kacis |
| YANGIN VAR | panik | yangin | orman-yangininda-kacis |
| telefonda sadece acil çağrı yazıyor | dolayli | telefon-pili-ve-sebeke | yardim-isareti-verme |
| geceleyin dağda mahsur kaldık fenerimiz var | dolayli | yardim-isareti-verme | dogada-kaybolma |
| nefes alamiyorum gibi hissediyorum cok korkuyorum | diakritiksiz | panik-ve-psikolojik-ilk-yardim | bilinc-ve-nefes |
| arkadaşım deprem sonrası konuşmuyor boş boş bakıyor ne yapabilirim | ses | panik-ve-psikolojik-ilk-yardim | deprem-sonrasi-ilk-adimlar |
| dagda yolumuzu sasirdik hava kariyor | diakritiksiz | dogada-kaybolma | kar-firtinasinda-aracta-mahsur |
| kamptaki atesi nasil tam olarak sonduruz | diakritiksiz | ates-yakma | yangin |
| yere yatınca soğuk içimize işliyor | dolayli | barinak-ve-soguktan-korunma | vucut-isisi |
| dağda kaldık hava kararıyor üstümüzü örtecek bir şey yok | ses | barinak-ve-soguktan-korunma | kar-firtinasinda-aracta-mahsur |
| suyumuz bitti etrafta dere falan yok | gunluk | su-bulma | sel-ve-su-baskini |
| deniz suyu içilirmi susadk | yazim_hatasi | su-bulma | su-aritma |
| akrep iğnesini batırdı ayağı şişiyo | gunluk | yilan-ve-akrep-sokmasi | ari-sokmasi-ve-alerjik-reaksiyon |
| YILAN | panik | yilan-ve-akrep-sokmasi | yardim-isareti-verme |
| Gök gürültülü fırtınada açık arazideysem ne yapmalıyım? | resmi | yildirim-ve-firtina | deprem-ani-disarida |
| yildirim carpan birine dokunulur mu | diakritiksiz | yildirim-ve-firtina | havayolu-tikanmasi |
| fırtnada çadırda kalmak güvenlimi | yazim_hatasi | yildirim-ve-firtina | deprem-ani-disarida |
| AĞAÇLAR YANIYOR | panik | orman-yangininda-kacis | ates-yakma |
