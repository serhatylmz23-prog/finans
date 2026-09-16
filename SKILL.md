---
name: bist-portfoy-terminali
description: TradingView Desktop'taki watchlist'i okuyup Fintables temel verisiyle birleştirir, tek ekranda ölçüm tablosu üretir. MUTLAKA kullan: "portföy raporu", "portföyüme bak", "portföy tara", "hisse detayı", "giriş zamanlaması", "portföy özeti", "pozisyonlarım ne durumda". Yatırım tavsiyesi, alım satım sinyali veya bias hükmü ÜRETMEZ.
---

# BIST Portföy Terminali

## Kullanıcı ayarı

```
WATCHLIST_ADI: portföy
VARSAYILAN_KAPSAM: 20
POZISYON_DOSYASI: ~/bist-terminal/portfoy.json
```

Bu üç satır dışında dosyada değiştirilmesi gereken yer yoktur.

`WATCHLIST_ADI`: TradingView'deki listenin adı. Sistem hisse isimlerini bu listeden okur, bu dosyada hisse kodu tutulmaz.

`VARSAYILAN_KAPSAM`: Tek raporda kaç sembol okunacağı. Aşılırsa kullanıcıya sorulur.

`POZISYON_DOSYASI`: Kâr zarar hesabı için isteğe bağlı dosya. Yoksa o katman atlanır.

## Değer önerisi

TradingView tek hisseyi tek ekranda gösterir, Fintables bilanço verir. Bu skill ikisini birleştirip tüm watchlist'i tek tabloya indirir. Kullanıcı her hisse için ayrı tıklama turu yapmak yerine tek komut çalıştırır.

## MUTLAK SINIR

Bu skill hüküm vermez. YASAK olanlar:

- "AL", "SAT", "TUT", "gir", "çık" gibi aksiyon önerisi
- "yükseliş eğilimi", "bullish", "bearish", "boğa", "ayı" gibi bias etiketi
- "ucuz", "pahalı", "cazip", "fırsat", "riskli" gibi değer yargısı
- Hedef fiyat, stop seviyesi, pozisyon büyüklüğü hesabı
- "şu seviyeden alınabilir" türü koşullu tavsiye
- Emir gönderme, emir ekranı açma, broker entegrasyonu kullanma

Skill SADECE ölçülen değeri bildirir. Yorumu kullanıcı yapar.

Kullanıcı "ne yapayım", "alayım mı" diye sorarsa: Tabloyu ver, kararın kendisine ait olduğunu tek cümleyle belirt, hüküm verme.

## Adım 0: Ön kontrol

Her çalıştırmada:

1. `tv_health_check` çalıştır, `cdp_connected: true` mu bak
2. False ise `tv_launch` ile TradingView Desktop'ı başlat, tekrar dene
3. Hâlâ bağlanmıyorsa dur, kullanıcıya bildir, teknik katman olmadan devam etme

## Adım 1: Watchlist'i oku

`WATCHLIST_ADI` değerindeki listeyi oku, sembol listesini al.

**Araç tespiti:** Bu MCP'de çok sayıda araç var, isimlerini varsayma. İlk çalıştırmada mevcut `mcp__tradingview__*` araçlarını listele, şu işleri yapanları tespit et: Watchlist okuma, sembol değiştirme, zaman dilimi değiştirme, indikatör ekleme, indikatör değeri okuma, bar verisi okuma. Tespit ettiğin eşleşmeyi oturum boyunca kullan.

Endeks sembollerini (XU100, XU030, XBANK gibi) portföy satırı olarak alma. Tablonun üstünde ayrı bir bağlam satırında göster.

Liste bulunamazsa kullanıcıya hangi listeleri gördüğünü sor, tahmin etme.

## Hacim disiplini

TradingView Kullanım Koşulları otomatik veri toplamayı kısıtlar (bkz. sondaki yasal uyarı). Tespit riski hacimle birlikte artar. Bu yüzden:

- Sürekli tarama, döngü veya arka planda izleme ASLA kurma
- Otomatik zamanlanmış tekrar kurma, rapor sadece kullanıcı istediğinde çalışır
- Aynı sembolü tek raporda birden fazla kez okuma
- Kullanıcı arka arkaya tarama isterse hatırlat: Rapor gün içinde birkaç kez çalıştırılmak için tasarlandı, sürekli izleme için değil
- Toplu backtest, optimizasyon veya çoklu parametre denemesi bu skill'in işi değildir, talep gelirse reddet

## Adım 2: Kapsam

Varsayılan: `VARSAYILAN_KAPSAM` değeri kadar sembol.

Liste bunu aşarsa önce süre uyarısı ver: "X sembol için tahmini süre Y dakika, devam edeyim mi". Sembol başına 2-4 saniye hesapla.

Kullanıcı belirli hisse sayarsa sadece onları oku.

## Adım 3: Teknik katman (TradingView)

Her sembol için oku:

| Değer | Zaman dilimi |
|---|---|
| Son fiyat ve günlük % değişim | Günlük |
| 50 günlük hareketli ortalamaya % mesafe | Günlük |
| 200 günlük hareketli ortalamaya % mesafe | Günlük |
| RSI (14) | Günlük |
| RSI (14) | Haftalık |
| 52 hafta zirvesine % mesafe | Haftalık |
| 52 hafta dibine % mesafe | Haftalık |
| Hacim / 20 günlük ortalama hacim oranı | Günlük |

Okunamayan değere `veri yok` yaz. Tahmin üretme, hesaplama uydurma.

Saatlik grafiği bu adımda ASLA açma.

Geçici olarak indikatör eklediysen iş bitince kaldır, grafiği kullanıcının bıraktığı hale döndür.

## Adım 4: Temel katman (Fintables)

Fintables MCP bağlı değilse bu katmanı atla, tabloda belirt, hata verme.

Her sembol için:

- Son açıklanan bilanço dönemi
- TMS 29 enflasyon düzeltmesi uygulanmış mı (gelir tablosunda "Net Parasal Pozisyon" kalemi var mı)
- F/K ve PD/DD
- Son 30 günde KAP bildirimi var mı, varsa başlıkları

Enflasyon düzeltmesi uygulanmamış hisselerde dönem karşılaştırması YAPMA, sadece işaretle.

Çektiğin verinin dönem etiketini ve yayınlanma tarihini mutlaka yaz.

F/K hesabında TTM net kâr negatifse `zarar` yaz, negatif çarpan üretme. Çarpan çok küçük bir paydadan doğuyorsa bunu veri notlarında belirt.

Temel katman özet tabloda F/K ve PD/DD olarak görünür, gerisi hisse detayında açılır.

## Adım 5: Pozisyon katmanı (opsiyonel)

`POZISYON_DOSYASI` yolundaki dosya VARSA oku, YOKSA bu katmanı sessizce atla, hata verme.

Dosya varsa her sembol için hesapla:
- Maliyete göre getiri %
- Pozisyon büyüklüğü (adet × son fiyat)
- Portföy içi ağırlık %

Dosyada olmayan sembol için o hücrelere `-` yaz.

Bu katman hesaplamadır, yorum değildir.

Kullanıcı adet ve maliyet vermediyse ASLA örnek veya varsayılan pozisyon üretme.

## Adım 6: Özet tablo

```
BIST PORTFÖY TERMİNALİ
[tarih saat] · [X] sembol · TradingView + Fintables
Endeks: [endeks kodu] [değer] ([günlük %])

| Hisse | Fiyat | Gün% | 50G | 200G | RSI-G | RSI-H | 52H Tepe | Hacim x | F/K | PD/DD |
|---|---|---|---|---|---|---|---|---|---|---|
```

Pozisyon dosyası varsa şu iki sütun eklenir: `Getiri%`, `Ağırlık%`

Sütun anlamları tablonun altına yazılır:
- 50G / 200G: Hareketli ortalamaya % mesafe, üstteyse artı
- RSI-G / RSI-H: Günlük ve haftalık RSI(14), Wilder
- 52H Tepe: 52 hafta zirvesine % mesafe
- Hacim x: Son gün hacmi / 20 günlük ortalama hacim, 1,0 = ortalama
- F/K: Piyasa değeri / TTM net kâr (ana ortaklık payı)
- PD/DD: Piyasa değeri / ana ortaklığa ait özkaynak

Tablonun altına ekle:
- Okunamayan sembol varsa listele
- Kapsam dışı kalan sembol sayısı ve nasıl açılacağı
- Fintables veri dönemi ve TradingView okuma zamanı
- TMS 29 durumu, düzeltme uygulanmamış hisseler ayrı listelenir
- Aykırı çarpan uyarıları
- "Bu tablo ölçüm bildirir, yatırım tavsiyesi içermez."

## Adım 7: Hisse detayı (talep üzerine)

```
[HİSSE KODU] · [tarih saat]

TEKNİK
[Adım 3'teki tüm değerler, günlük ve haftalık ayrı]

TEMEL (Fintables)
Son bilanço dönemi · Enflasyon düzeltmesi durumu · F/K · PD/DD · Son KAP bildirimleri

POZİSYON (dosya varsa)
Adet · Maliyet · Getiri % · Büyüklük · Ağırlık

KAYNAK
TradingView: [okuma zamanı] · Fintables: [veri dönemi]
```

## Adım 8: Giriş zamanlaması modu (talep üzerine)

SADECE kullanıcı "giriş zamanlaması" dediğinde çalışır, varsayılan raporda asla.

Saatlik grafikte oku:
- Saatlik RSI (14)
- Günün en yüksek ve en düşük seviyesi
- Son fiyatın gün içi aralıktaki konumu (%)

Bu modda da hüküm verme. "Gün içi aralığın üst %20'sinde" de, "beklenmeli" deme.

## Adım 9: HTML gösterge panosu (talep üzerine)

Kullanıcı pano isterse `~/bist-terminal/raporlar/` altına tarihli tek dosya yaz.

Kurallar:
- Koyu zemin, tek renk vurgu, okunaklı tablo
- Sütun başlıklarına tıklayınca sıralanabilsin
- Pozitif yeşil, negatif kırmızı
- RSI 70 üstü ve 30 altı görsel olarak ayrışsın
- Her satırda son 30 günün fiyat çizgisi, inline SVG
- Altta veri notları, en altta yatırım tavsiyesi uyarısı
- Tek dosya, dış bağımlılık yok, çevrimdışı açılsın

Panoya hüküm, yorum veya iyi kötü etiketi ekleme.

Not: TradingView'in gömülü widget script'i `file://` protokolünde kendini iframe ile değiştiremediği için sorun çıkarır. Canlı grafik gömmek gerekiyorsa dosyayı yerel sunucu üzerinden aç.

## Hata durumları

| Durum | Davranış |
|---|---|
| TradingView bağlı değil | tv_launch dene, olmazsa dur ve bildir |
| Watchlist bulunamadı | Mevcut listeleri göster, kullanıcıya sor |
| Sembol grafikte açılmadı | O satıra `sembol bulunamadı`, devam et |
| İndikatör okunamadı | O hücreye `veri yok`, devam et |
| Fintables bağlı değil | Temel sütunları atla, tabloda belirt |
| Pozisyon dosyası yok | Sessizce atla, o sütunları gösterme |

Hiçbir durumda eksik veriyi tahminle doldurma. Rakam uydurma, örnek veri üretme.

## Kapsam

Bu skill portföy izleme katmanıdır.

Emsal karşılaştırma, kriter taraması, tek şirket araştırması veya sektör analizi bu skill'in işi değildir. Kullanıcı bunları isterse ayrı bir çalışma olduğunu belirt.

## Yasal uyarı ve sorumluluk

Bu skill, TradingView Desktop uygulamasıyla Chrome DevTools Protocol üzerinden çalışan yerel bir MCP sunucusuna dayanır.

**Bilinmesi gerekenler:**

- TradingView Kullanım Koşulları'nın 3. maddesi otomatik veri toplama yöntemlerini kısıtlar. Bu kurulum o koşullarla çelişebilir.
- Araç TradingView sunucularına bağlanmaz, dosyalarını değiştirmez, ağ trafiğini dinlemez. Yalnızca kullanıcının kendi bilgisayarında çalışan uygulamayla konuşur. Buna rağmen hesap banı riski vardır.
- TradingView ilk ihlallerde geçici, tekrarlayan ihlallerde kalıcı ban uygular. Bu tür banlar hesabın tüm grafik özelliklerini etkiler.
- Kullanım kişisel, eğitim ve araştırma amaçlıdır. Sorumluluk tamamen kullanıcıya aittir.

**Bu skill ile yapılmayacaklar:**

- TradingView piyasa verisini yeniden dağıtmak, satmak veya ticari olarak kullanmak
- TradingView'in erişim kontrollerini veya abonelik sınırlarını aşmak
- Çıkarılan veriyle otomatik alım satım veya algoritmik karar üretmek
- Pine Script yazarlarının fikri haklarını ihlal etmek

Kullanıcı bunlardan birini isterse skill reddeder ve sebebini belirtir.

**Kaynak:** MCP sunucusu `tradesdontlie/tradingview-mcp` (MIT lisansı). Yazarlar hesap banlarından, askıya almalardan veya kullanımdan doğan başka sonuçlardan sorumlu değildir.

Bu skill ve ürettiği çıktılar yatırım tavsiyesi içermez.
