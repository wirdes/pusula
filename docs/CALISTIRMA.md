# Pusula'yı çalıştırma ve test etme

Bu rehber, Pusula'nın arama katmanını bilgisayarda nasıl çalıştırıp deneyeceğini ve telefonda (iOS) nasıl çalışacağını anlatır.

> **Şu anki durum:** Pusula'nın kendi Türkçe dil modeli henüz eğitilmedi. Şimdilik hazır modellerle (en iyisi ModernBERT-TR-Embed) arama yapılıyor. Kartların hepsi taslaktır ve bir sağlık profesyoneli tarafından onaylanmadı; gerçek bir acil durumda kullanılmamalıdır.

## Bilgisayarda (Windows)

### 1. Kurulum

Python 3.11 gerekir. Sanal ortamı ve model önbelleğini OneDrive gibi senkronize klasörlerin **dışında** tutun; modeller yüzlerce MB tutar.

```bash
py -3.11 -m venv C:/Users/<kullanici>/.venvs/pusula
```

```bash
C:/Users/<kullanici>/.venvs/pusula/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

```bash
C:/Users/<kullanici>/.venvs/pusula/Scripts/python -m pip install -r requirements.txt
```

Aşağıdaki komutlarda `python`, bu sanal ortamdaki Python'dur. Komutları repo klasöründe çalıştırın. Ekran kartı gerekmez; işlemci (CPU) yeterlidir.

### 2. Modeli bir kez indir

Modeller ilk kullanımda Hugging Face önbelleğine (`C:/Users/<kullanici>/.cache/huggingface`) iner. Bunun için bir kez internet gerekir:

```bash
python scripts/ask.py --online "deneme"
```

Varsayılan model ModernBERT-TR-Embed'dir (149M parametre, diskte birkaç yüz MB). Bundan sonra internet gerekmez.

### 3. Kendi sorunu dene

```bash
python scripts/ask.py
```

Soru yazıp Enter'a basın; çıkmak için boş bırakın. Tek bir soru da verebilirsiniz:

```bash
python scripts/ask.py "enkaz altindayim nefes almakta zorlaniyorum"
```

Araç, benzerlik skoruna göre üç şekilde cevap verir:

| Skor | Cevap |
|---|---|
| 0,58 ve üstü | Eminim: kartın özeti, adımları ve yapılmaması gerekenler gösterilir |
| 0,50 – 0,58 | Emin değilim: en yakın üç kart listelenir, kullanıcı seçer |
| 0,50'nin altı | "Bu konuda bir kartım yok. Hayati bir durumsa 112'yi ara." |

Eşikler küçük ve aynı yazar tarafından hazırlanmış bir test setinden seçildi (bkz. [`scripts/ask.py`](../scripts/ask.py)). Gerçek kullanıcı sorularıyla yeniden ayarlanmaları gerekir.

Başka bir modelle karşılaştırmak için:

```bash
python scripts/ask.py --model e5-small
```

Seçenekler: `bm25`, `bm25-f5`, `static-mrl-multilingual`, `minilm-l12-multilingual`, `e5-small`, `bert-turkish-nli-stsb`, `modernbert-tr-embed`, `bge-m3`. Eşikler şimdilik yalnızca ModernBERT-TR-Embed için tanımlı; diğer modellerde her zaman en iyi kart gösterilir.

### 4. Gerçekten çevrimdışı çalıştığını doğrula

`ask.py` varsayılan olarak internete hiç çıkmaz. Emin olmak için Wi-Fi'yi kapatıp aynı komutu çalıştırın. Ekranda görebileceğiniz "Could not reach the Hub ... offline mode is enabled" mesajı normaldir; model yerel önbellekten yüklenir.

### 5. Toplu ölçüm

Kartları ve test sorularını doğrulamak için:

```bash
python scripts/validate.py
```

Tüm modelleri 214 test sorusuyla ölçmek için (ilk seferde sekiz yöntemin kullandığı altı modeli, toplam birkaç GB, indirir):

```bash
python scripts/retrieval_baseline.py
```

Sonuçlar [`results/baseline.md`](../results/baseline.md) dosyasına yazılır, yorumları [`results/README.md`](../results/README.md) içindedir. Kart ya da soru eklediğinizde bu iki komutu yeniden çalıştırın.

### macOS ve Linux

Adımlar aynıdır; yalnızca sanal ortam komutları farklıdır:

```bash
python3.11 -m venv ~/.venvs/pusula
```

```bash
~/.venvs/pusula/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

```bash
~/.venvs/pusula/bin/python -m pip install -r requirements.txt
```

## Telefonda (iOS, PusulaApp)

Telefonda çalıştırmak **henüz mümkün değil**. Uygulama, ayrı bir repoda Swift ile yazılacak **PusulaApp** olacak. Planlanan yol:

1. **Modeli dönüştürme:** Arama modeli `coremltools` ile Core ML biçimine çevrilir ve 8 bit'e sıkıştırılır. ModernBERT-TR-Embed bu haliyle yaklaşık 150 MB tutar; Pusula'nın kendi 20–60M'lik modeli ise birkaç on MB olacak.
2. **Kartları önceden işleme:** Kartların vektörleri bilgisayarda bir kez hesaplanır ve uygulamayla birlikte bir dosya olarak gelir. Telefonda yalnızca kullanıcının sorusu işlenir.
3. **Swift tarafı:** Tokenizer (ör. Hugging Face'in `swift-transformers` kütüphanesi), Core ML ile soru vektörünün hesaplanması, kartlarla benzerlik ve yukarıdaki üç bölgeli eşik mantığı.
4. **Cihazda ölçüm:** Bir soru için süre, bellek kullanımı ve pil tüketimi gerçek bir iPhone'da ölçülür.

Bu adımlar hazır olduğunda bu bölüm, uygulamanın Xcode'da nasıl derlenip test edileceğini anlatacak şekilde güncellenecek. O zamana kadar modeli denemenin yolu, yukarıdaki bilgisayar adımlarıdır.

## Sorun giderme

- **Türkçe karakterler bozuk görünüyor:** Windows Terminal kullanın. Betikler çıktıyı UTF-8 olarak yazar.
- **Model dosyalarının önbellekte bulunamadığını söyleyen bir hata:** Model henüz inmemiş. Komutu bir kez `--online` ile çalıştırın.
- **İlk soru yavaş:** Model ilk soruda belleğe yüklenir; sonraki sorular daha hızlıdır (bilgisayar işlemcisinde soru başına yaklaşık 40 ms).
