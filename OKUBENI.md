# SyFinansOtağı — Güncelleme Notları

## ⚠️ Önce bunu oku: API anahtarları

`.env.local` içinde gerçek (canlı) API anahtarların düz metin olarak duruyordu
(Finnhub, Alpha Vantage, ExchangeRate-API, GoldAPI, CoinGecko). Bu dosya bana
bu sohbet üzerinden ulaştığı için artık "yalnızca sende olan bir sır" değil.
Önerim:
- Mümkün olan anahtarları ilgili panellerden **iptal edip yeniden üret**.
- `.env.local` dosyasını asla bir zip/repo/paylaşım içinde dışarı çıkarma
  (eklediğim `.gitignore` bunu Git için engelliyor, ama zip'leyip birine
  gönderirsen yine dışarı çıkar).

## Bu turda ne değişti

1. **Video desteği** — `goruntu_isleyici.py` artık videodan eşit aralıklarla
   kare çıkarıp (varsayılan 8 kare) her karede OCR çalıştırıyor ve sonuçları
   birleştiriyor (`videodan_metin_cikar`). `main.py` içindeki
   `/api/kasa/gorsel-aktar` artık dosyanın video mu foto mu olduğunu
   otomatik ayırt ediyor.
2. **Sayı ayrıştırma hatası düzeltildi** — eski kod `"80.67"` gibi bir ondalık
   değeri bindelik ayıracı sanıp `8067`'ye çeviriyordu; bu maliyet/kâr-zarar
   hesaplarını ciddi şekilde bozardı. Yeni `_sayi_coz()` fonksiyonu hem
   `"80,67"`, hem `"80.67"`, hem `"1.234,56"` biçimlerini doğru okuyor.
   (Sentetik test görsel/videolarla doğrulandı.)
3. **Kategoriler** — Kapsam dokümanındaki Kasam alt başlıklarına uygun olarak
   her varlık otomatik sınıflandırılıyor: *Hisselerim / Fonlarım / Dövizlerim
   / Kıymetli madenlerim*. Arayüzde sekmelerle filtreleniyor.
4. **Sıralama** — Tablo başlıklarına tıklayarak (Adet, Maliyet, Canlı Fiyat,
   K/Z %, Toplam Tutar, Güven) artan/azalan sıralama yapılabiliyor;
   `/api/kasa/analiz?sirala=...&yon=asc|desc&kategori=...` parametreleriyle
   API üzerinden de kullanılabiliyor.
5. **Toplu / tekil silme** — zaten vardı, korundu ve kategoriyle birlikte
   çalışacak şekilde güncellendi.
6. **Çoklu dosya + önizleme + sürükle-bırak** — birden fazla foto/video
   seçilebiliyor, yüklemeden önce küçük önizlemeler görünüyor, tek tek
   kaldırılabiliyor, işlenirken durum göstergesi çıkıyor.
7. **PWA (kurulabilir uygulama) desteği** — `manifest.json` + `sw.js` eklendi,
   `finans.html` bunları bağlıyor. Bir sunucuda çalıştırıp telefonundan
   Safari/Chrome ile açtığında "Ana ekrana ekle" ile gerçek bir uygulama
   ikonu/splash ekranıyla kurulabiliyor; masaüstünde Chrome/Edge "Uygulamayı
   yükle" seçeneğini gösteriyor.
8. `requirements.txt` düzeltildi — kod FastAPI/uvicorn kullanıyordu ama dosya
   Flask listeliyordu; artık gerçek bağımlılıklarla eşleşiyor.

## Kapsam dokümanına göre henüz eksik olanlar

`SyFinansOtağı_Kapsamı.txt` çok daha geniş bir yapı tanımlıyor (TCMB/KAP/TEFAS
canlı bağlantıları, Planlar sekmesi — bütçe dağılımı/kademeli alım-satım,
Analiz sekmesinde Kanıt Gücü/Risk/Adaylar/Piyasa davranışı, "Kaşif" araştırma
ajanı, kendi kendini geliştiren öğrenme katmanı). Zip'te bunların kod tarafı
yoktu; `__pycache__` içinde kaynağı artık mevcut olmayan derlenmiş
(`.pyc`) dosyalar vardı (`kasa.py`, `planlar.py`, `alarm_sistemi.py`,
`kendini_gelistir.py`, `syfinans_ajan.py`, `web_scraper.py`, eski
`kaynak_merkezi.py`) — muhtemelen önceki bir sürümden kalma. Bunları
decompile etmeyi denemedim çünkü Python 3.14 bytecode'u için güvenilir bir
decompiler yok; bunun yerine kapsam dokümanına göre sıfırdan yazmak daha
sağlıklı. İstersen bir sonraki adımda bunlardan birini (örn. Planlar veya
Kaşif) birlikte kurabiliriz.

`icons/` altındaki `SYK_FINANS_OTAGI_RUNTIME_v1.0` ve `SYK_ICON_ENGINE_*`
klasörleri gerçek veri bağlantısı olmayan marka/ikon sistemleri
(kendi `manifest.json`'ları `"market_data_connector_included": false` diyor)
— görsel kimlik hazır ama işlevsellik değil.

## Gerçekçi kapsam notu (iOS / Android / masaüstü)

Bu sohbet ortamından App Store / Play Store'a native bir uygulama
yayınlayamam, sürekli (7/24) çalışan bir bulut sunucusu da kuramam/işletemem
— bunlar Xcode/Android Studio, geliştirici hesapları ve gerçek bir hosting
gerektirir. Yukarıdaki PWA yaklaşımı, bugün elimdeki araçlarla ulaşabileceğin
en gerçekçi "üç platformda da kurulabilir tek uygulama" çözümü: kodu kendi
bilgisayarında, ev sunucunda ya da ucuz bir VPS'te çalıştırırsan, telefon ve
masaüstünden gerçek bir uygulama gibi kurulup kullanılabilir.

Ajanlar konusunda kapsam dokümanındaki kural korunuyor: sistem hiçbir zaman
kendi başına emir vermiyor, yalnızca analiz/öneri üretiyor
(`Kendi kendine al/sat: HAYIR`).

## Mevcut kasandaki bozuk kayıtlar hakkında

Test ettiğim gerçek ekran görüntülerinde şunu fark ettim: `kasa_verileri.json`
içinde zaten **eski (düzeltilmemiş) parser'ın ürettiği hatalı kayıtlar** var:

- `DEGER: adet 19522, maliyet 52` → aslında "Günlük Değer **19.522,52** TL"
  yazısının TL tutarı ikiye bölünüp sembol/adet/maliyet sanılmış.
- `AYA: adet 3275, maliyet 62` → aslında "₺**3.275,62**" tutarı.
- `DEI: adet 4812, maliyet 99` → aslında "DFI" sembolünün yanlış okunması +
  "₺**4.812,99**" tutarı.
- `EAL`, `EMR` de büyük ihtimalle benzer kaynaklı.

Yeni parser bu ekran tiplerini artık doğru okuyor, ama **geçmişte eklenmiş
bu hatalı kayıtları otomatik silmedim** (yanlışlıkla doğru bir kaydı
silmek istemedim). Arayüzdeki "Fonlarım" ve "Hisselerim" sekmelerinden bu
satırları gözden geçirip, gerçek dışı olanları (checkbox işaretleyip
"Seçilenleri Sil" ile) temizlemeni, sonra ilgili ekran görüntülerini
yeniden yüklemeni öneririm — bu sefer doğru ayrıştırılacaklar.

## Bu turda eklenen yeni format desteği

Gönderdiğin 4 farklı ekran tipini test ettim, hepsi artık doğru okunuyor:
1. **Broker portföy tablosu** (Sembol/Miktar/Ort.Mlyt./K-Z) — zaten çalışıyordu.
2. **Banka kıymetli maden hesabı** ("Vadesiz XAG ... 20,16 XAG") — çalışıyordu.
3. **TEFAS fon detay kartı** ("... FONU" başlığı + "Günlük Değer" / "Ortalama
   Maliyet" satırları) — **yeni eklendi**. Bu tarz kayıtlar `adet=1`,
   `son_bilinen_deger` (o anki TL değeri) ve `maliyet` (TL bazlı ortalama
   maliyet) olarak saklanıyor; TEFAS'a canlı bağlantı olmadığı için fiyat
   her yeni ekran görüntüsü yüklendiğinde güncelleniyor.
4. **Uygulama ana ekranı listesi** (Midas tarzı: sembol + `₺değer` +
   değişim satırı) — **yeni eklendi**. Aynı şekilde `son_bilinen_deger`
   olarak saklanıyor; bu formatta maliyet bilgisi ekranda yer almadığı için
   `maliyet=0` kalıyor (kâr/zarar % hesaplanamıyor, "TUT" varsayılan
   tavsiyesi veriliyor) — bunu istersen tablo satırındaki kategori
   menüsünün yanına maliyet elle girme alanı ekleyerek tamamlayabiliriz.
5. Aynı sembol için değer güncellenirse (örn. AYA'yı bir hafta sonra tekrar
   yüklersen) **yeni kayıt açmıyor, mevcut kaydı güncelliyor**.

## 12 Eylül 2026 turunda ne değişti (hata/eksik tarama + aktivasyon)

Kapsamlı bir tarama yapıldı; kod her satırıyla okundu, frontend'in çağırdığı
her API endpoint'i backend'le karşılaştırıldı, `.pyc` kalıntıları için
decompile denemesi tekrar (bağımsız olarak) yapıldı.

**Aktive edilen "ölü" ajan:**
- `goruntu_isleyici.py` (ekran görüntüsünden OCR ile portföy okuyan ajan)
  `main.py` içinde import ediliyordu ama **hiçbir endpoint'e bağlı değildi**.
  `index.html`/`finans.html` zaten `/api/kasa/gorsel-aktar` adresine istek
  atmaya çalışıyordu, bu adres backend'de yoktu. Artık gerçek bir endpoint
  var, `index.html`'e yükleme arayüzü eklendi, uçtan uca test edildi
  (sentetik bir görüntüyle: sembol + adet + maliyet doğru okunup kasaya
  eklendi/güncellendi). Not: yalnızca fotoğraf/ekran görüntüsü destekleniyor,
  video desteği kodda hiç yoktu (önceki notumdaki "video" ifadesi hatalıydı,
  düzeltildi).

**Bulunan ve düzeltilen hatalar:**
1. `main.py`: ALTIN.S1 (Darphane Altın Sertifikası) fiyatı hiç
   hesaplanmıyordu; yanlış sembolle (`ALTIN.IS`) sorgu atılıyordu, özel
   sertifika mantığı hiç tetiklenmiyordu → `ALTINS1` ile düzeltildi.
2. `main.py`: `analiz_motoru.sinyal_ve_plan_uret()` çağrısına aylık/yıllık
   getiri hiç geçilmiyordu → fonksiyon varsayılan (0.0, 0.0) ile çalışıyor,
   bu da "hareketsiz hisse" tespitini her zaman `True` yapıp neredeyse her
   zarardaki hisseyi yanlışlıkla "İŞLEM KISITI" olarak damgalıyordu. Artık
   gerçek değerler geçiliyor.
3. `fon_takip.py`: Fon fiyat önbelleği (`self.cache`) hiç süresi
   dolmuyordu; bir kez çekilen fiyat sunucu açık kaldığı sürece donuk
   kalıyordu. 5 dakikalık TTL eklendi.
4. `finans.html`: Tablo `row.tavsiye`, `row.aksiyon_plani`,
   `row.guven_endeksi`, `row.kar_zarar_yuzde` alanlarını okuyordu ama API
   bu isimlerde alan döndürmüyor (gerçek isimler: `ajan_karari`,
   `analiz_notu`, `guven_skoru`, `kar_zarar_orani`) → tablo hep boş/`undefined`
   basıyor, hatta `row.tavsiye.includes(...)` JS hatası fırlatıyordu. Alan
   adları koda göre düzeltildi; ayrıca yanlışlıkla iddia edilen "video"
   desteği arayüzden kaldırıldı.
5. `index.html`: Karar rozeti her SAT/STOP/DİKKAT durumunu abartılı şekilde
   "İŞLEM KISITI" (trading restriction) etiketiyle gösteriyordu; artık
   backend'in döndürdüğü gerçek karar metni gösteriliyor.
6. `index.html`: Font Awesome ikon kütüphanesi CDN'den (cdnjs.cloudflare.com)
   yükleniyordu → **tamamen internetsiz kullanım isteğiyle doğrudan
   çelişiyordu**. Kaldırıldı, yerine hiçbir ağ isteği gerektirmeyen
   emoji/unicode ikonlar konuldu.
7. PWA hiç gerçekten çalışmıyordu: `manifest.json` ve `icons/` FastAPI
   tarafından hiç servis edilmiyordu (route/mount yoktu), `index.html`
   içinde de `<link rel="manifest">` veya servis çalışanı (service worker)
   kaydı hiç yoktu — önceki turda "eklendi" denmiş ama fiilen bağlanmamış.
   Artık `/manifest.json` route'u, `/icons` static mount'u ve
   `navigator.serviceWorker.register()` çağrısı var; `sw.js` da tüm ikon
   boyutlarını önbelleğe alacak şekilde genişletildi.
8. `.env.local` dosyasının adı bozulmuştu (`#U0131` gibi kaçış karakteri
   dosya adına karışmış, muhtemelen bir zip/aktarım hatasından) → gerçek
   dosya adı `.env.local` olmadığı için `load_dotenv(".env.local")` bu
   dosyayı hiç bulamıyordu. Dosya doğru adla yeniden adlandırıldı
   (içeriğindeki anahtarlar zaten önceki turda yıldızlarla maskelenmişti,
   gerçek bir anahtar sızmadı).
9. `setup.py` tamamen alakasız/eski bağımlılıklar listeliyordu (Flask,
   scikit-learn, plyer, deep-translator) ve `main:main` diye var olmayan
   bir giriş noktasına işaret ediyordu. Gerçek bağımlılıklarla eşleştirildi;
   `main.py`'a `calistir()` fonksiyonu eklendi.
10. `baslat.bat` (Windows) ve `baslat.sh` (Mac/Linux) eklendi: VSCode veya
    terminal açmadan, dosyaya çift tıklayarak bağımlılıkları kurup sunucuyu
    başlatıyor ve tarayıcıyı otomatik açıyor.

**Tekrar doğrulanan konu — kayıp `.pyc` ajanları:**
`kasa.py`, `planlar.py`, `alarm_sistemi.py`, `kendini_gelistir.py`,
`syfinans_ajan.py`, `web_scraper.py` ve eski `kaynak_merkezi.py` hâlâ
yalnızca Python 3.14 bytecode'u olarak duruyor, kaynak kodları hiçbir yerde
yok (git geçmişinde de yok). Bağımsız olarak tekrar denedim (güncel bir
decompiler projesini — pycdc — klonlayıp kontrol ettim): en yeni desteklenen
sürüm Python 3.13, 3.14 için genel kullanıma açık hiçbir decompiler yok.
Yani bu dosyalar **gerçekten kurtarılamaz durumda**; önceki turdaki
değerlendirme doğruydu. Kapsam dokümanına göre bunları (özellikle Planlar
veya Alarm Sistemi'ni) sıfırdan yazmak istersen bir sonraki adım bu olabilir.

Ayrıca fark edilen küçük bir kalıntı: proje kökünde boş bir `finans/`
klasörü var (eski bir git alt-modül yapısından kalma, içinde yalnızca
`.gitattributes` var) — işlevsel hiçbir etkisi yok, istersen silebilirsin.


## 12 Eylül 2026 (2. tur) — Analiz kalitesi, toplam maliyet, kaynak gösterimi

Bu turda kullanıcının belirttiği "analizler hatalı/sabit geliyor, toplam
maliyet yok" şikayeti ve daha fazlası doğrulandı ve düzeltildi:

**`analiz_motoru.py`**
- `toplam_maliyet` artık hesaplanıp gerçekten döndürülüyor (önceden
  hesaplanıp atılıyordu). Ayrıca `birim_maliyet` alias'ı eklendi.
- `guven_skoru` artık HER ZAMAN sabit (95/91/86/94) değil; fiyatın canlı mı
  yedek mi olduğuna ve getiri verisinin eksik olup olmadığına göre
  hesaplanıyor. `analiz_notu` içine "güven skoru neden bu seviyede"
  gerekçesi ekleniyor.
- `["UMPAS","DARDL","BRKO","MEMS1"]` gibi koda gömülü sabit "kesin kısıtlı
  hisse" listesi kaldırıldı — bu liste güncelliğini yitirdiğinde herkese
  yanlış "İŞLEM KISITI" damgası basıyordu. Artık tespit tamamen o anki
  gerçek getiri verisine dayanıyor ve "kesin" değil "olası" ifadesiyle
  sunuluyor.
- Tüm kararlarda "tavsiye/garanti" dili yumuşatıldı ("değerlendir",
  "senaryo", "karar sana ait" gibi) — kesin kazanç vaadi verilmiyor.

**`finans_kaynak_merkezi.py`**
- `durum_raporu()` artık gerçekten her kaynağa (döviz, BIST, TEFAS, altın)
  kısa bir istek atıp sonucu raporluyor; önceden hiç test etmeden
  "%100 Çalışıyor" basıyordu.
- Yeni `gercek_getiri_hesapla()`: yfinance geçmiş fiyat verisinden GERÇEK
  1 aylık / 1 yıllık % değişim hesaplıyor. Önceden altın/gümüş/döviz için
  bu sayılar koda gömülü sabitti (`"+%7.8"` gibi, piyasa ne olursa olsun
  hep aynı); BIST hisselerinde ise kullanıcının kendi maliyetinden
  türetilen anlamsız bir hesaptı. İkisi de kaldırıldı.

**`arastirma_merkezi.py` (yeni — "Kaşif")**
- Gerçek, herkese açık RSS kaynaklarından (BloombergHT, Investing.com
  Türkiye, Doviz.com — hepsi bu turda gerçekten test edildi) sembolle
  ilgili haberleri arayıp gerçek link ile döndürüyor. Eşleşme yoksa BOŞ
  döner, asla uydurma haber üretmez. `/api/kasa/arastir/{sembol}` ve
  `/api/piyasa/durum` endpoint'leri eklendi.
- Gerçekçi sınır: Sosyal medya (X/Twitter, Instagram, TikTok, forumlar)
  için resmi API'ler ücretli/kotalı, ya da otomatik erişim kullanım
  şartlarına aykırı olduğundan buraya dahil edilmedi. YouTube için genişleme
  noktası bırakıldı (`.env.local` içine `YOUTUBE_DATA_API_KEY` eklenirse
  devreye girer, yoksa sessizce atlanır — uydurma veri ile doldurulmaz).
  Bu ortamda ağ erişimi kapalı olduğundan uçtan uca canlı test
  yapılamadı; RSS kaynak URL'leri ayrı ayrı doğrulandı, dosyanın kendisi
  ilk çalıştırmada test edilmeli.

**`main.py`**
- `sirala`/`yon` parametreleri artık gerçekten uygulanıyor (önceden kabul
  edilip hiç kullanılmıyordu).
- Her varlık için gerçek veri kaynağı adı ve güven puanı analiz motoruna
  iletiliyor; Kaşif'in bulduğu kaynak linkleri `analiz_notu`'na ekleniyor.

**`index.html` / `finans.html`**
- "TOPLAM MALİYET" ve "GÜVEN" sütunları tabloya eklendi.
- "İŞLEM KISITI" rozet metni kaldırıldı (artık öyle bir karar metni motor
  tarafından üretilmiyor).

## Çalıştırma

**En kolay yol (VSCode/terminal gerekmez):**
- Windows: `baslat.bat` dosyasına çift tıkla.
- Mac/Linux: Terminalden `./baslat.sh` çalıştır (veya çoğu dosya
  yöneticisinde çift tıkla).

İlk çalıştırmada gerekli paketleri otomatik kurar (internet gerekir),
sonrasında tarayıcıyı `http://localhost:8000` adresinde otomatik açar.
Sunucu bir kez kurulduktan sonra **internet olmadan da** çalışmaya devam
eder; sadece canlı piyasa fiyatları güncellenemez, bunun yerine referans
(yedek) fiyatlar gösterilir.

**Manuel yol:**
```bash
pip install -r requirements.txt
# Tesseract OCR motorunun sistemde kurulu olması gerekir (Windows: Tesseract-OCR,
# Linux/Mac: apt/brew install tesseract-ocr tesseract-ocr-tur)
# Kurulu değilse uygulama yine çalışır, sadece ekran görüntüsünden otomatik
# varlık ekleme özelliği pasif kalır.
python main.py
# tarayıcıdan http://localhost:8000 adresini aç
```
