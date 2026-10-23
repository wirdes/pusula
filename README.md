# Pusula

İnternet ve şebeke olmadan telefonda çalışan, Türkçe bir deprem ve acil durum asistanı.

> **Durum:** Erken geliştirme aşamasında, henüz kullanıma hazır değil.

## Amaç

Deprem gibi afetlerde internet ve mobil şebeke çoğu zaman çöker. Pusula, telefona önceden indirilmiş ve doğrulanmış bilgileri tamamen çevrimdışı olarak bulup sunmayı hedefliyor.

## Yaklaşım

- **Önce arama:** Cevaplar uzmanlarca kontrol edilmiş bilgi kartlarından gelir; model kendi başına tavsiye üretmez.
- **Sabit protokoller:** Kalp masajı ve kanama kontrolü gibi kritik adımlar karar ağacı olarak tutulur.
- **Küçük modeller:** Türkçe arama (embedding) modeli, durum sınıflandırıcı, diakritik ve noktalama düzeltici.
- **Pil dostu:** Varsayılan mod hafif aramadır; büyük dil modeli isteğe bağlıdır.
- **Sesli kullanım:** Çevrimdışı konuşma tanıma ve sesli okuma (planlanıyor).

## Yol haritası

- [ ] Bilgi kartı formatı ve ilk kartlar
- [ ] Türkçe test soruları
- [ ] Hazır embedding modelleriyle çevrimdışı arama ölçümü
- [ ] Küçük Türkçe arama modelinin eğitimi
- [ ] Android prototipi

## Uyarı

Pusula bir bilgilendirme aracıdır. Tıbbi cihaz değildir ve profesyonel yardımın yerini tutmaz. Ulaşabiliyorsanız her zaman 112'yi arayın.

## Lisans

Henüz bir lisans seçilmedi. Lisans eklenene kadar tüm hakları saklıdır.
