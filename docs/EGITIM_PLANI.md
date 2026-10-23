# Pusula modeli eğitim planı

Bu belge, Pusula'nın kendi küçük Türkçe dil modelinin nasıl eğitileceğini anlatır. Model, telefonda internetsiz çalışacak ve kullanıcının mesajını doğru bilgi kartına ya da karar akışına eşleyecek bir **arama (embedding) modeli**dir; metin üreten bir LLM değildir.

> Süre, boyut ve maliyet rakamlarının **tahmin** olarak işaretlenenleri ölçülmedi. Diğer sayılar [`results/`](../results/README.md) altındaki ölçümlerden gelir.

## Hedef ve başarı ölçütleri

Bugünkü en iyi hazır model ModernBERT-TR-Embed (149M parametre). Pusula'nın kendi modeli bu modelin **öğrencisi** olacak: ondan ve sentetik veriden öğrenip telefona sığacak kadar küçük kalacak.

| Ölçüt | Bugün (ModernBERT-TR-Embed, akışlarla) | Hedef |
|---|---|---|
| Doğru kart ya da akış ilk sırada (hit@1) | %81 | ≥ %81 |
| İlk üçte (hit@3) | %95 | ≥ %95 |
| Zıt talimatlı kartın ilk sırada çıkması | 0 | 0 |
| Kapsam dışı soruları ayırma (AUROC) | 0,93 | ≥ 0,90 |
| Türkçe karaktersiz sorularda hit@1 | %76 | ≥ %85 |
| Panik halindeki kısa sorularda hit@1 | %60 | ≥ %70 |
| Boyut | 149M | ≤ 60M parametre, 8 bit'te ≤ 60 MB |
| iPhone'da soru başına süre | ölçülmedi | < 50 ms (ölçülecek) |

Öğrencinin öğretmeni geçmesi beklenen yerler Türkçe karaktersiz ve hatalı yazım. Sentetik veride bu tür örnekler bilerek bol tutuluyor.

Ölçümler [`eval/queries.jsonl`](../eval/queries.jsonl) üzerinde yapılır. Bu set **eğitimde hiçbir zaman kullanılmaz.** Modelin yayımlanma kararı ise ileride toplanacak, insanların yazdığı bağımsız test setine göre verilir.

## Dört aşama

```
1. Sentetik soru üretimi  ->  1b. Yargıç  ->  2. Veri seti kurma  ->  3. Öğrenci eğitimi  ->  4. Telefona hazırlama
   generate_queries.py        judge_queries.py    build_dataset.py         (sıradaki adım)          budama, 8 bit, Core ML
```

### 1. Sentetik soru üretimi ([`scripts/generate_queries.py`](../scripts/generate_queries.py))

Açık lisanslı bir LLM'e her kart için, gerçek bir kullanıcının yazabileceği mesajlar yazdırılır.

- **Kapsam:** 38 kart × 5 yazım tarzı × 2 tur × 10 mesaj ≈ 3.800 mesaj, artı kart başına 5 "benzeyen ama ilgisiz" soru (≈ 190). Toplam 418 istek.
- **Yazım tarzları:** resmi, günlük, panik, dolaylı (konunun adı geçmeden), sesli (konuşma tanıma çıktısı gibi). Türkçe karaktersiz ve yazım hatalı halleri LLM'e değil, kurala dayalı olarak 2. aşamada eklenir; böylece kontrol edilebilir kalır.
- **Yazanlar:** Her tur farklı bir kişi tipiyle: kendisi için, yakını için, yanındaki bir yabancı için, yaşlı, genç, sağlık bilgisi olmayan biri.
- **Zıt talimatlı kartlar:** Bir karar akışına bağlı kartlar için LLM'e kartın hangi kartla karışabileceği söylenir ve iki durumu ayıran ayrıntıyı (nefes alıp almadığı, sıcak mı soğuk mu olduğu) mesajlara katması istenir.
- **Kapsam dışı sorular:** "Mangal için hangi kömür" gibi, kartlara kelime olarak benzeyen ama acil durumla ilgisi olmayan sorular. Bunlar "bilgim yok" eşiğini ayarlamak için kullanılır.

**Üretici model seçenekleri** (yalnızca çıktısıyla model eğitmeye izin veren lisanslar):

| Seçenek | Model | Lisans | Nerede çalışır | Maliyet | Süre (tahmin) |
|---|---|---|---|---|---|
| A | gpt-oss-120b | Apache-2.0 | Hugging Face Inference Providers (bu makinede kayıtlı HF hesabıyla) | Birkaç dolardan az (tahmin) | 1 saatten az |
| B | gpt-oss-20b | Apache-2.0 | Yerel, llama.cpp (Vulkan) ile RX 9070 XT üzerinde; ~12 GB indirme | Ücretsiz | 1–3 saat |
| C | Qwen3-14B | Apache-2.0 | Yerel, llama.cpp ile; ~9 GB indirme | Ücretsiz | 2–4 saat |

gpt-oss-120b, Türkçe genel değerlendirme setinde (TurkBench) en yüksek puanı alan açık model. Bu yüzden mesajların Türkçe kalitesi açısından en güçlü seçenek bu. Yerel seçenekler ise tamamen ücretsiz ve internetsiz çalışır.

Claude ve kapalı API'ler (OpenAI, Gemini) eğitim verisi üretmek için **kullanılmaz**, çünkü şartları çıktılarıyla başka model eğitmeyi kısıtlıyor. Test soruları ile kart taslaklarını Claude yazdı. Test soruları eğitime girmez. Kart metinleri ise uzman incelemesinden geçip yeniden yazılacak; kartlar değiştiğinde öğrenci yeniden eğitilir.

**Seçilen üretici:** Seçenek A, Hugging Face Inference Providers üzerinden DeepInfra'da `openai/gpt-oss-120b` (1M token başına 0,04 $ giriş, 0,17 $ çıkış). Bir istek ortalama yaklaşık 1.000–1.500 çıkış token'ı kullanıyor (modelin düşünme metni dahil), 10 mesaj için maliyet yaklaşık 0,0002 $.

**Pilot bulguları** (dört pilot, toplam maliyet ≈ 0,03 $; ham mesajlar `data/synthetic/pilot1..3/` altında):

| Pilot | Görülen sorun | Düzeltme |
|---|---|---|
| 1 | Mesajların ≈ %15'i sorunlu: anlamsız panik mesajları ("KOPAR TUT!"), "Anne," gibi hitaplar, kart özetini tekrar eden belirti listeleri, kalp masajı kartına "bebek" ya da "suda boğulma" yazılması | İstem sıkılaştırıldı: anlamsız mesaj, hitap, belirti listesi ve kapsam dışı durum yasak |
| 1 | Bilinci kapalı biri için "kendisi için soran" kişi tipi; tüm kartlara aynı genel "nefes / sıcak-soğuk / enkaz" ipucu verildiği için kalp masajı mesajlarında "vücudu soğuk" | Kişi tipi düzeltildi; her kart artık yalnızca kendi akışının sorularını görüyor |
| 1 | Öğretmen filtresi, zıt kart çiftlerinde doğru mesajları atıp anlamsızları tutuyor (öğretmen bu çiftleri karıştırıyor) | Öğretmen kontrolü akış düzeyinde: yalnızca "doğru durum mu" sorusuna bakılıyor |
| 2 | Mesajlar akışın sorusunu kopyalıyor ("Kişinin alnına ve gövdesine dokunduğumda..."); kalıplaşma | Soruları ve kelimelerini kopyalama yasağı; "aynı cümle kalıbını tekrar etme" kuralı |
| 3 | Mesajlar kartın talimatlarını sıralıyor ("Valfi sık, dışarı!") ya da uygulamış gibi anlatıyor; gaz mesajları "gaz" demediği için yangınla karışıyor | İstemden kartın adımları çıkarıldı, "kişi ne yapacağını bilmiyor" kuralı eklendi; konunun gündelik adını kullanmak serbest bırakıldı |
| 4 | Kalan gürültü ≈ %5 (ör. içeriksiz "Şimdi ne yapmalı?") | Yargıç adımı bunları büyük ölçüde temizliyor |

Betik kaldığı yerden devam edebilir ve `--max-dollars` ile belirlenen tahmini harcamaya ulaşınca durur.

### 1b. Yargıç ([`scripts/judge_queries.py`](../scripts/judge_queries.py))

Üreticiden **farklı bir model ailesinden** bir LLM her mesajı kartıyla birlikte okur ve iki soruyu cevaplar: mesaj **doğal** mı (ne yapacağını bilmeyen gerçek bir insanın yazabileceği anlamlı bir mesaj mı) ve **uygun** mu (gerçekten bu kartı mı gerektiriyor, başka bir kartı ya da hiçbir kartı değil). Hayır cevabı alan mesajı `build_dataset.py` atar.

- **Model:** DeepInfra'da `Qwen/Qwen3-235B-A22B-Instruct-2507` (Apache-2.0; 0,09 $ / 0,55 $). Farklı aile seçildi, çünkü aynı model ailesi kendi hatalarını görmekte zorlanır.
- **Kartın ölçütleri esas:** Yargıç, kartın tüm adımlarını ve akış sorularının hangi cevabının hangi karta gittiğini görür, ve kendi tıbbi yorumunu değil kartın ölçütlerini kullanması istenir. Bu kural pilotta önemli bir hatayı düzeltti: yargıç ilk başta "hırıltılı soluyor" diyen mesajları "nefes alıyor, yan yatırma kartı uygun" diye reddediyordu. Oysa ERC kılavuzuna ve kalp masajı kartına göre yalnızca hırıltılı, düzensiz soluma kalp durması belirtisidir ve kalp masajı gerektirir.
- **Pilotta:** 110 mesajdan 13'ünü reddetti. Ret verdiklerinin neredeyse hepsi elle yapılan incelemede de sorunluydu. Biraz katı davranıyor; yanlışlıkla iyi bir mesajı atmak, kötü bir mesajı tutmaktan daha ucuz bir hata.

### 2. Veri seti kurma ([`scripts/build_dataset.py`](../scripts/build_dataset.py))

| Adım | Ne yapar |
|---|---|
| Yargıç kararı | `data/synthetic/judgments/` altındaki kararlara göre reddedilen mesajları atar. |
| Temizlik | Boş, çok kısa ya da çok uzun mesajları ve tekrarları atar; numaralandırmayı temizler. |
| Sızıntı kontrolü | Test setindeki bir sorunun birebir kopyasını, kelime kökleri %75'ten fazla örtüşen mesajları ve öğretmen modelde test sorusuna anlamca neredeyse özdeş olanları (benzerlik ≥ 0,95) atar. "nefes almıyor" gibi kısa test ifadelerini *içeren* mesajlar atılmaz; yoksa en önemli eğitim sinyali de silinirdi. |
| Varyantlar | Türkçe karaktersiz (%50), yazım hatalı (%35) ve sesli/noktalamasız (%25) halleri ekler. |
| Öğretmen kontrolü | ModernBERT-TR-Embed, LLM'in yazdığı her mesajın kartını ilk 5'e koymuyorsa o mesajı ve varyantlarını ayırır; inceleme için `rejected.jsonl` dosyasına yazar. Bir karar akışına bağlı kartlar tek bir kart gibi sayılır, çünkü öğretmen tam bu çiftleri karıştırıyor; hangi taraf olduğu üretim talimatından gelir. Varyantlar ayrıca yargılanmaz, çünkü öğretmen tam da bu gürültüde zayıf. |
| Zor negatifler | Her mesaj için öğretmenin doğru karttan sonra en yüksek puan verdiği 3 kart. Zıt talimatlı kart çiftleri doğal olarak burada çıkar. |
| Bölme | Her kartın ana mesajlarının %10'u geliştirme (dev) setine ayrılır. Bir mesaj ve varyantları her zaman aynı tarafta kalır. |

**İlk tam üretimin sonucu (2026-10-23):**

| | Sayı |
|---|---|
| Üretilen mesaj (418 istek) | 3.980 (3.811 kart mesajı + 169 kapsam dışı) |
| Yargıcın reddettiği | 480 (%12) |
| Öğretmenin ayırdığı ana mesaj / bunların varyantları | 204 / 179 |
| Tekrar | 16 |
| Test setine benzediği için atılan | 0 |
| **Eğitim / geliştirme / kapsam dışı** | **5.530 / 630 / 169** |
| Kart başına eğitim örneği | 85 – 174 |
| Toplam harcama (pilotlar dahil, tahmini) | ≈ 0,21 $ |

Ayrıntılar: [`data/stats.md`](../data/stats.md). En zayıf kart, 85 örnekle panik ve psikolojik ilk yardım. Öğretmen bu karttan 43 ana mesaj ayırdı. Bunların bir kısmı gerçekten belirsiz ("kalbim çarpıyor, nefesim kesiliyor" panik de olabilir, kalp krizi de) ve ayrılması güvenli. Bu inceleme, **göğüs ağrısı ve kalp krizi** için bir kartın eksik olduğunu da gösterdi.

Çıktılar `data/` klasörüne yazılır:

| Dosya | İçerik |
|---|---|
| `train.jsonl`, `dev.jsonl` | `query`, `card`, `style`, `variant`, `base_id`, `hard_negatives`, `teacher_rank`, `teacher_top` |
| `oos.jsonl` | Kapsam dışı sorular ve öğretmenin en yakın bulduğu kart |
| `rejected.jsonl` | Öğretmenin ayırdığı mesajlar ve nedeni |
| `stats.md` | Atılanlar, varyantlar, tarzlar ve kart başına örnek sayısı |

### 3. Öğrenci eğitimi (sıradaki adım)

**Aday modeller:**

| Aday | Boyut | Lisans | Bugün (hit@1, akışlarla) | Rolü |
|---|---|---|---|---|
| multilingual-e5-small | 118M; bunun ≈ 96M'i kelime tablosu | MIT | %65 | **Ana aday.** Kelime tablosu Türkçeye budanınca ≈ 30–35M (tahmin). |
| paraphrase-multilingual-MiniLM-L12-v2 | 118M | Apache-2.0 | %55 | Yedek aday; aynı budama uygulanabilir. |
| ModernBERT-TR-Embed, ince ayarlı | 149M | Apache-2.0 | %81 | Üst sınır. iPhone'a sığar ve yeterince hızlıysa en güçlü seçenek. |
| Model2Vec statik model | 8–30 MB | MIT | ölçülmedi | Eski telefonlar ve pil tasarrufu modu; öğretmenden damıtılır. |

**Yöntem:**

- **Ana kayıp:** MultipleNegativesRankingLoss. Mesajı doğru kartın vektörüne yaklaştırır; aynı paketteki diğer kartlardan ve zor negatiflerden uzaklaştırır.
- **Öğretmenden damıtma (isteğe bağlı):** Öğrencinin kartlara verdiği skor dağılımını öğretmeninkine yaklaştırır (`teacher_top` veri setinde hazır). Öğretmenin zayıf olduğu varyantlarda uygulanmaz.
- **Başlangıç ayarları:** öğrenme hızı 2e-5 – 5e-5, paket 32–64, 2–4 tur, mesaj için 64, kart için 256 token, ısınma %10. Dev setinde en iyi MRR'yi veren ağırlıklar tutulur.
- **Ezber kontrolü:** Kart sayısı az (38) olduğu için model kartları ezberleyebilir. Birkaç kart eğitimden tamamen çıkarılıp modelin bu kartları hâlâ bulup bulamadığı ayrıca ölçülür. Yeni kart eklendiğinde bu sonuca göre yeniden eğitim gerekip gerekmediğine karar verilir.

**Donanım:** RX 9070 XT, ROCm ile PyTorch. Bu makinedeki `ahenk-rocm` ortamında torch 2.12 + ROCm 7.14'ün kartı tanıdığı ve temel işlemleri doğru yaptığı doğrulandı. Pusula için aynı PyTorch sürümüyle ayrı bir ortam kurulacak. e5-small'un ≈ 5.500 örnekle birkaç turluk eğitimi dakikalar sürer (tahmin). GPU sorun çıkarırsa kiralık bir RTX 4090 saatte ≈ 0,34 dolar.

### 4. Telefona hazırlama

1. **Kelime tablosu budama:** Türkçe metinlerde (kartlar, eğitim verisi, Türkçe bir metin örneklemi) hiç görülmeyen token'lar atılır. Doğruluk değişmemeli; budamadan önce ve sonra ölçülür.
2. **8 bit sıkıştırma** ve kaybın ölçülmesi.
3. **Core ML dönüşümü**, kart vektörlerinin önceden hesaplanıp uygulamaya gömülmesi.
4. **Eşiklerin yeniden ayarlanması:** "bilgim yok" ve "emin değilim" eşikleri (bugün 0,50 / 0,58) yeni model için dev ve kapsam dışı verisiyle yeniden seçilir.

Ayrıntılar için: [`docs/CALISTIRMA.md`](CALISTIRMA.md), iOS bölümü.

## Riskler ve önlemler

| Risk | Önlem |
|---|---|
| Test setinin eğitime sızması | Sızıntı kontrolü; test seti eğitimde hiç kullanılmaz; yayın kararı insan test setiyle verilir. |
| Sentetik verinin tekdüze olması | 5 yazım tarzı × 6 kişi tipi, kurala dayalı varyantlar, yüksek örnekleme sıcaklığı; `stats.md` ile dağılım kontrolü; pilotta gözle inceleme. |
| Öğretmenin zayıf noktalarını öğrenciye aktarmak | Öğretmen filtresi yalnızca ana mesajlarda ve ilk 5 toleransıyla; varyantlar filtrelenmez. |
| Modelin kartları ezberlemesi | Kart dışarıda bırakma testi; kartlar değişince yeniden eğitim. |
| Lisans | Yalnızca Apache-2.0 ve MIT lisanslı üretici, öğretmen ve öğrenci modeller. |
| Kartların taslak olması | Model, kartlar bir sağlık profesyoneli tarafından onaylanmadan gerçek kullanıcıya sunulmaz. |

## Yol haritası

| Adım | İş | Süre (tahmin) |
|---|---|---|
| 1 | Üretici model seçimi ve pilot üretim (10 istek), gözle kontrol | 1 gün |
| 2 | Tam üretim (418 istek) ve veri seti kurma | 1 gün |
| 3 | Eğitim betiği ve ROCm ortamı | 1–2 gün |
| 4 | e5-small ve MiniLM eğitimi, ölçüm, hata analizi | 2–3 gün |
| 5 | Kelime tablosu budama, 8 bit, yeniden ölçüm | 1–2 gün |
| 6 | İnsan test seti: 5–10 kişi, kartları görmeden 300–500 soru (diğer adımlarla paralel) | 1–2 hafta |
| 7 | Core ML dönüşümü ve PusulaApp'te deneme | PusulaApp'e bağlı |

## Komutlar

Önce çalıştırmadan üretilecek istemleri görmek için:

```bash
python scripts/generate_queries.py --dry-run
```

Hugging Face üzerinden üretim (kullanılan ayar; önce `--limit 10` ile pilot yapın):

```bash
python scripts/generate_queries.py --base-url https://router.huggingface.co/v1 --model openai/gpt-oss-120b:deepinfra --hf-token --price-in 0.04 --price-out 0.17 --max-dollars 0.50
```

Yerel bir llama.cpp sunucusuyla üretim (sunucu `http://127.0.0.1:8080` üzerinde çalışıyorken):

```bash
python scripts/generate_queries.py --base-url http://127.0.0.1:8080/v1 --model gpt-oss-20b --price-in 0 --price-out 0 --limit 10
```

Mesajları yargılatmak için:

```bash
python scripts/judge_queries.py --base-url https://router.huggingface.co/v1 --model Qwen/Qwen3-235B-A22B-Instruct-2507:deepinfra --hf-token --price-in 0.09 --price-out 0.55 --max-dollars 0.50
```

Veri setini kurmak için:

```bash
python scripts/build_dataset.py
```
