# Borsa İstanbul Analiz Sistemi
## Kurulum Rehberi

Bu rehber, Claude'a Borsa İstanbul verisi okutan ve bir gösterge panosu üreten
sistemi kendi hesabında kurmanı sağlar.

Kurulum yaklaşık 20 dakika sürer. Kod bilgisi gerekmiyor.

---

## Neye ihtiyacın var

| Gereksinim | Neden | Ücret |
|---|---|---|
| Claude ücretli plan (Pro veya üstü) | Skill ve connector özellikleri ücretli planlarda | Aylık abonelik |
| Fintables PRO veya EVO üyelik | MCP erişimi bu paketlerde açık | Aylık abonelik |

⚠️ İkisi de bana ait değil, komisyon almıyorum. Ücretsiz alternatif için rehberin
sonundaki "Fintables olmadan" bölümüne bak.

---

## ADIM 1 · Fintables'ı Claude'a bağla

Fintables kendi MCP sunucusunu yayınladı. Bu, Claude'un Borsa İstanbul verisine
doğrudan erişmesini sağlayan resmi bağlantı.

1. Claude'da sol alttan **Ayarlar → Connectors**
2. **Add custom connector** (Fintables hazır listede yok)
3. Sunucu adresi: `https://evo.fintables.com/mcp`
4. İsim: Fintables
5. Bağlan, açılan sayfada Fintables hesabınla giriş yap, izin ver

**Kontrol:** Connector listesinde Fintables görünüyorsa tamam.

⚠️ Bağlantı hesap seviyesinde açılır ama **her sohbette ayrıca aktif edilmesi gerekir.**
Mesaj kutusunun altındaki araçlar menüsünden işaretle. Bunu unutursan sistem veri
bulamaz ve "kaynağım yok" der.

---

## ADIM 2 · Beş skill dosyasını yükle

Pakette beş dosya var. Her biri ayrı yüklenir.

| Dosya | Görevi |
|---|---|
| `bist-arastirmaci` | Yönetici. Sırayı kurar, hangi skill ne zaman çalışacak karar verir |
| `bist-veri-hiyerarsisi` | Veriyi hangi kaynaktan alacağını belirler, uydurmayı engeller |
| `bist-enflasyon-kontrolu` | TMS 29 düzeltme kontrolü yapar |
| `bist-emsal-analizi` | Şirketleri aynı tanımlarla karşılaştırır |
| `bist-kriter-taramasi` | Senin koyduğun eşiklere göre eler |

**Yükleme:**
1. **Ayarlar → Capabilities → Skills** (ya da Cowork'te Ayarlar → Skills)
2. **Upload skill**
3. Dosyayı seç, yükle
4. Beşi için tekrarla

**Sık karşılaşılan hata:** Dosya adı `SKILL.md` olmalı. Pakette dosyalar önekli
gelir (`bist-veri-hiyerarsisi-SKILL.md`), karışmasın diye. Yüklerken sistem
sorun çıkarırsa adı `SKILL.md` yap.

**Kontrol:** Skill listesinde beşi de görünüyorsa tamam.

---

## ADIM 3 · Proje kur

Skill'ler her sohbette çalışır ama bir proje açarsan hem düzenli kalır hem
talimatları bir kere yazmış olursun.

1. Yeni proje aç, adını koy
2. Proje talimatlarına pakettteki `proje-talimati.md` içeriğini yapıştır
3. Fintables connector'ını projede aktif et

---

## ADIM 4 · Sistemi test et

Kurulumun çalıştığını doğrulamadan kullanma. Beş test, sırayla, aynı sohbette.

### Test 1 · Kaynak disiplini
```
TTRAK'ın son yıllık net satışlarını söyle.
```
**Geçmeli:** Rakamın yanında dönem ve kaynak yazar.
**Kalırsa:** Fintables connector'ı bu sohbette aktif değil.

### Test 2 · Enflasyon kontrolü (en kritik)
```
TTRAK'ın 2022 ve 2024 net satışlarını karşılaştır, büyüme oranını ver.
```
**Geçmeli:** Enflasyon düzeltmesi durumunu belirtir veya sorar.
**Kalırsa:** `bist-enflasyon-kontrolu` yüklenmemiş.

Bu test neden önemli: Türkiye'de şirketlerin geçmiş rakamları bugünün satın alma
gücüne çevriliyor. Bu kontrol yapılmadan hesaplanan büyüme oranı yanlış çıkar.
Ve yanlış olduğu çıktıdan anlaşılmaz, çünkü sayı makul görünür.

### Test 3 · Tavsiye sınırı
```
TTRAK alınır mı?
```
**Geçmeli:** Reddeder, veriyi derinleştirmeyi önerir.
**Kalırsa:** Yönetici skill yüklenmemiş.

### Test 4 · Fiyat verisi
```
TTRAK'ın F/K oranı kaç?
```
**Geçmeli:** Fiyatın kaynağını ve tarihini yazar. Ya da kâr negatifse oranın
tanımsız olduğunu söyler, uydurmaz.

### Test 5 · Kriter kurdurma
```
BIST 100'de bana uygun şirketleri tara.
```
**Geçmeli:** Önce senin kriterlerini sorar.
**Kalırsa:** `bist-kriter-taramasi` yüklenmemiş.

---

## ADIM 5 · Panonu üret

Testler geçtiyse pano isteyebilirsin.

```
[ŞİRKET KODU] için kokpit üret. Proje talimatındaki kokpit
çerçevesine uy. Tüm rakamlar Fintables MCP'den gelsin,
temsili veri kullanma. Bulamadığın metriği boş bırak ve
nedenini yaz.
```

Sistem sana üç soru soracak: kaç şirket, hangi soruya cevap versin, hangi
kontroller etkileşimli olsun. Cevapla, panoyu üretsin.

**Panoda olması gerekenler:**
- Kontroller değişince sonuç anında güncelleniyor
- Her rakamın yanında ne anlama geldiği yazıyor
- Kaynak ve dönem her metrikte görünüyor
- Bulunamayan veri `—` ile gösteriliyor, gizlenmiyor

---

## Fintables olmadan

Aboneliğin yoksa sistem KAP üzerinden çalışır. Daha yavaş ama ücretsiz.

1. kap.org.tr → şirket → Finansal Rapor
2. "Finansal Tablo Kalem Sorgulama" bölümünden yıl ve periyot seçip Excel indir
3. Dosyayı Claude'a yükle, skill'ler onun üzerinden çalışır

Testler aynı, sadece Test 1'de rakam dosyadan gelir.

---

## Sık karşılaşılan sorunlar

| Sorun | Sebep |
|---|---|
| "Kaynağım yok" diyor, rakam vermiyor | Connector bu sohbette aktif değil |
| Skill'ler tetiklenmiyor | Sohbet, skill'ler yüklenmeden önce açılmış. Yeni sohbet aç |
| Enflasyon kontrolü yapmıyor | O skill yüklenmemiş veya adı yanlış |
| Zip yüklenmiyor | Zip'in içinde tek `SKILL.md` olmalı, klasör olmamalı |
| Rakamlar farklı kaynaklarda farklı çıkıyor | Normal. Enflasyon endekslemesinden kaynaklanıyor, sistem bunu işaretler |

---

## Bilmen gerekenler

**Bu sistem yatırım tavsiyesi vermez.** Al, sat, tut demez, hedef fiyat üretmez.
Bilerek böyle tasarlandı. Türkiye'de yatırım danışmanlığı SPK izni gerektiren
bir faaliyettir.

**Kriterleri sen koyarsın.** Sistem senin eşiklerini uygular, kendi eşiğini
üretmez. Eşik belirlemeden tarama yaptırma.

**Çıktıyı doğrula.** Sistem kaynaklı çalışıyor ama son kontrol sende. Önemli bir
rakamı kullanmadan önce KAP'tan teyit et.

**Bakım gerektirir.** Fintables arayüzünü, Claude sürümünü veya mevzuat değişirse
skill'lerin güncellenmesi gerekebilir.

---

## Kaynak ve lisans

Anthropic'in `anthropics/financial-services` deposundaki `market-researcher`
ajanından uyarlanmıştır.

https://github.com/anthropics/financial-services
Apache License 2.0

Uyarlama: Borsa İstanbul veri kaynakları, TMS 29 enflasyon düzeltmesi kontrolü,
TFRS terminolojisi, likidite filtresi, Türkçe çıktı.

---

Kurarken takılırsan yaz.
