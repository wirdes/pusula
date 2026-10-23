# Çevrimdışı arama ölçümü

- Tarih: 2026-10-23
- Kart sayısı: 24 (hepsi taslak), soru sayısı: 136 (16 kapsam dışı)
- Kart metni: title, summary, keywords, steps
- Donanım: PC işlemcisi (CPU), sorgular tek tek kodlandı. Süreler telefonda farklı olur, yalnızca modelleri kıyaslamak içindir.

## Genel sonuç

| Model | Parametre (M) | hit@1 | hit@3 | MRR | Kapsam dışı AUROC | Sorgu süresi (ms) |
|---|---|---|---|---|---|---|
| bm25-f5 | – | 90 | 98 | 94 | 0.93 | 0.0 |
| bge-m3 | 568 | 90 | 97 | 93 | 0.94 | 71.3 |
| modernbert-tr-embed | 149 | 88 | 98 | 93 | 0.97 | 39.4 |
| bm25 | – | 83 | 92 | 88 | 0.87 | 0.0 |
| bert-turkish-nli-stsb | 111 | 76 | 91 | 84 | 0.94 | 20.4 |
| e5-small | 118 | 76 | 91 | 84 | 0.88 | 9.1 |
| static-mrl-multilingual | 108 | 65 | 85 | 77 | 0.83 | 0.3 |
| minilm-l12-multilingual | 118 | 63 | 81 | 74 | 0.93 | 9.0 |

hit@1: doğru kart ilk sırada (%). hit@3: ilk üçte (%). MRR: ortalama ters sıra (%). AUROC: kapsam dışı soruları en yüksek benzerlik skoruna bakarak ayırabilme (0,5 rastgele, 1,0 kusursuz).

## Soru tipine göre hit@1 (%)

| Model | resmi | gunluk | diakritiksiz | yazim_hatasi | panik | dolayli | ses |
|---|---|---|---|---|---|---|---|
| bm25-f5 | 75 | 96 | 100 | 83 | 100 | 92 | 80 |
| bge-m3 | 100 | 96 | 87 | 100 | 43 | 92 | 60 |
| modernbert-tr-embed | 100 | 83 | 87 | 92 | 86 | 88 | 60 |
| bm25 | 62 | 88 | 96 | 75 | 100 | 92 | 60 |
| bert-turkish-nli-stsb | 92 | 88 | 70 | 75 | 29 | 76 | 40 |
| e5-small | 96 | 71 | 70 | 83 | 57 | 72 | 60 |
| static-mrl-multilingual | 54 | 83 | 70 | 67 | 43 | 60 | 60 |
| minilm-l12-multilingual | 79 | 71 | 57 | 58 | 14 | 68 | 40 |

## En iyi modelin (bm25-f5) ilk sırada bulamadığı sorular

| Soru | Tip | Beklenen | Bulunan ilk kart |
|---|---|---|---|
| Deprem sırasında evin içindeysem ne yapmam gerekiyor? | resmi | deprem-ani-bina-ici | deprem-sonrasi-ilk-adimlar |
| yatakta uyurken her şey titremeye başladı kalkayım mı | dolayli | deprem-ani-bina-ici | havayolu-tikanmasi |
| Araç kullanırken deprem olursa ne yapmalıyım? | resmi | deprem-ani-aracta | deprem-sonrasi-ilk-adimlar |
| sallantı durdu şimdi ne yapıcaz | gunluk | deprem-sonrasi-ilk-adimlar | deprem-ani-aracta |
| enkazın altnda kaldm ne yapcam | yazim_hatasi | enkaz-altinda-kalma | ezilme-yaralanmasi |
| karşı binada bir çocuk sesi duyuyoruz yardım ekibi yok ne yapalım | ses | enkazdaki-birine-yardim | panik-ve-psikolojik-ilk-yardim |
| şok geçiren birne ne yaplır | yazim_hatasi | sok | deprem-cantasi |
| Boğazına yiyecek kaçan birine nasıl yardım ederim? | resmi | havayolu-tikanmasi | deprem-cantasi |
| Donma tehlikesi geçiren birini nasıl ısıtırım? | resmi | hipotermi | enkazdaki-birine-yardim |
| Bina içinde yangın çıkarsa nasıl tahliye olmalıyım? | resmi | yangin | deprem-ani-bina-ici |
| Elektrik çarpan birine nasıl müdahale edilir? | resmi | elektrik-carpmasi | deprem-sonrasi-ilk-adimlar |
| depreme hazırlık için evde neler bulundurmalıyız | dolayli | deprem-cantasi | deprem-sonrasi-ilk-adimlar |
