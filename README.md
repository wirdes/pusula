# Pusula

İnternet ve şebeke olmadan telefonda çalışan bir **Türkçe dil modeli** ve **deprem / acil durum asistanı**.

Pusula'nın merkezinde, acil durum diline özel olarak eğitilecek küçük bir **Türkçe dil modeli** var. Bu model ChatGPT gibi metin üreten büyük bir dil modeli (LLM) değil. Görevi, panik halinde, Türkçe karakter kullanılmadan ya da hatalı yazılmış soruları anlayıp doğru bilgi kartını bulmak. Telefonda internetsiz çalışabilmesi için birkaç on milyon parametre gibi küçük bir boyutta tutulacak.

> **Durum:** Erken geliştirme aşamasında, henüz kullanıma hazır değil. Şu anda hazır modellerle ölçüm yapılıyor; Pusula'nın kendi modeli henüz eğitilmedi.

## Amaç

Deprem gibi afetlerde internet ve mobil şebeke çoğu zaman çöker. Pusula, telefona önceden indirilmiş ve doğrulanmış bilgileri tamamen çevrimdışı olarak bulup sunmayı hedefliyor.

## Yaklaşım

- **Önce arama:** Cevaplar uzmanlarca kontrol edilmiş bilgi kartlarından gelir; model kendi başına tavsiye üretmez.
- **Sabit protokoller:** Kalp masajı ve kanama kontrolü gibi kritik adımlar karar ağacı olarak tutulur.
- **Küçük modeller:** Türkçe arama (embedding) modeli, durum sınıflandırıcı, diakritik ve noktalama düzeltici.
- **Pil dostu:** Varsayılan mod hafif aramadır; büyük dil modeli isteğe bağlıdır.
- **Sesli kullanım:** Çevrimdışı konuşma tanıma ve sesli okuma (planlanıyor).

## Yol haritası

- [x] Bilgi kartı formatı ve 38 kart: sağlık, deprem, hayatta kalma, doğa ve tehlikeler (taslak, uzman onayı bekliyor)
- [x] Türkçe test soruları (214 soru, 8 tip)
- [x] Hazır embedding modelleriyle çevrimdışı arama ölçümü ([sonuçlar](results/README.md))
- [ ] Kartların bir sağlık profesyoneli tarafından incelenmesi
- [ ] İnsanların yazdığı bağımsız test seti
- [ ] Zıt talimatlı durumlar için karar akışları (nefes alıyor / almıyor, sıcak / soğuk)
- [ ] Uygulama özelliklerine yönlendiren niyetler (toplanma alanı, konum paylaşma, acil numaralar, fener, düdük)
- [ ] Resmi kaynaktan doğrulanmış acil numaralar ve toplanma alanı verisi
- [ ] Küçük Türkçe arama modelinin eğitimi
- [ ] iOS uygulaması: **PusulaApp** (Swift, ayrı repoda)

## Repo düzeni

| Klasör | İçerik |
|---|---|
| [`cards/`](cards/) | Bilgi kartları (YAML) ve kart formatının açıklaması |
| [`eval/`](eval/) | Türkçe test soruları ve soru tipleri |
| [`scripts/`](scripts/) | Doğrulama ve arama ölçüm betikleri |
| [`results/`](results/) | Ölçüm sonuçları |

## Geliştirme

Model dosyaları büyük olduğu için sanal ortamı ve model önbelleğini OneDrive dışında tutun. Modeller ilk çalıştırmada Hugging Face önbelleğine (`~/.cache/huggingface`) iner.

```bash
py -3.11 -m venv C:/Users/<kullanici>/.venvs/pusula
C:/Users/<kullanici>/.venvs/pusula/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
C:/Users/<kullanici>/.venvs/pusula/Scripts/python -m pip install -r requirements.txt
```

Kartları ve soruları doğrulamak için:

```bash
python scripts/validate.py
```

Hazır modellerle çevrimdışı arama ölçümü için:

```bash
python scripts/retrieval_baseline.py            # ilk sefer modelleri indirir
python scripts/retrieval_baseline.py --offline  # internete hiç çıkmadan çalışır
```

## Uyarı

Pusula bir bilgilendirme aracıdır. Tıbbi cihaz değildir ve profesyonel yardımın yerini tutmaz. Ulaşabiliyorsanız her zaman 112'yi arayın.

## Lisans

Henüz bir lisans seçilmedi. Lisans eklenene kadar tüm hakları saklıdır.
