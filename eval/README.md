# Test soruları

`queries.jsonl` dosyasındaki her satır, gerçek bir kullanıcının yazabileceği bir soru ve bu soruya karşılık gelmesi gereken kart(lar)dır.

```json
{"id": "q032", "text": "KAN DURMUYOR", "expected": ["ciddi-kanama"], "type": "panik"}
```

- `expected` listesindeki kartlardan herhangi biri bulunursa isabet sayılır. Listenin ilk elemanı asıl beklenen karttır.
- Kapsam dışı sorularda `expected` boş bırakılır. Bu sorular, uygulamanın "bu konuda bilgim yok" diyebilmesi için bir eşik belirlemekte kullanılır.

## Soru tipleri

| Tip | Ne ölçer | Örnek |
|---|---|---|
| `resmi` | Düzgün, eksiksiz yazılmış soru | Deprem sırasında evin içindeysem ne yapmam gerekiyor? |
| `gunluk` | Konuşma dili, kısaltmalar | ev sallanıyo şu an napıyım |
| `diakritiksiz` | Türkçe karakter kullanılmadan yazım | enkaz altindayim nefes almakta zorlaniyorum |
| `yazim_hatasi` | Aceleyle yazılmış, harf eksik | kanamyı nasl durdurrm |
| `panik` | Çok kısa, büyük harfli, panik halinde | KAN DURMUYOR |
| `dolayli` | Durumu tarif eden ama konuyu adlandırmayan soru | annemin kolu saatlerdir taşın altında sıkışmış |
| `ses` | Konuşma tanımadan çıkmış gibi, noktalamasız | arkadaşım bayıldı uyandıramıyoruz nefes de almıyor gibi |
| `kapsam_disi` | Hiçbir kartla ilgisi olmayan soru | dolar kuru bugün ne kadar |

## Bilinen sınırlamalar

- Soruların hepsi kartlarla aynı anda ve aynı yazar (Claude) tarafından yazıldı. Ölçüm sonuçları gerçek kullanıcı sorularına göre iyimser olabilir.
- Kartlardaki `keywords` alanı bu sorularla büyük ölçüde örtüşüyor. Bu yüzden asıl ölçüm anahtar kelimeler olmadan yapılır; `python scripts/validate.py` örtüşmeleri uyarı olarak listeler.
- Güvenilir bir ölçüm için gerçek insanların yazdığı, kartları görmeden hazırlanmış bir test setine ihtiyaç var. Bu set dondurulmalı ve eğitim verisinde kullanılmamalıdır.
