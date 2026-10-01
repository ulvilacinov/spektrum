# Almanca Kelime Antrenörü

Almanca → Türkçe kelime öğrenme uygulaması: PDF yükle, AI bölümleri ve kelimeleri çıkarsın,
kelimeleri gruplar hâlinde öğren, quiz'le pekiştir, zayıf kelimeleri tekrar et.

- `backend/` — FastAPI + PostgreSQL + seçilebilir yapay zekâ ([backend/README.md](backend/README.md))
- `frontend/` — React arayüzü ([frontend/README.md](frontend/README.md))
- `docs/SPEC.md` — ürün tanımı
- Canlı: **https://spektrum-kelime.fly.dev** (Fly.io + Neon; aşağıda "İnternette yayın")

## Kendi bilgisayarında çalıştırma

Gerekenler (bir kere): Docker Desktop, Python 3.12, Node.js 20+ ve `backend/.env`
(`backend/.env.example` dosyasının kopyası). Yapay zekâ sağlayıcısını, modelini ve API
anahtarını her kullanıcı sitede **⚙️ Ayarlar** sayfasından kendisi seçer. Backend'in sanal ortamı
kurulu olmalı (`backend/README.md` → Setup).

```powershell
.\start.ps1
```

Script sırasıyla Docker'ı bekler, PostgreSQL'i başlatır, migration'ları uygular, frontend'i
derler ve sunucuyu başlatır. Arayüz ve API aynı adreste: **http://localhost:8000**.
Durdurmak için `Ctrl+C`.

- `.\start.ps1 -SkipBuild` — frontend'i yeniden derlemeden başlatır (daha hızlı).
- `.\start.ps1 -Listen 127.0.0.1` — yalnızca bu bilgisayardan erişim.
- `.\start.ps1 -Port 8080` — başka bir port.
- "running scripts is disabled" hatası alırsan bir kere şunu çalıştır:
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- Geliştirme sunucusu (`uvicorn --reload`) 8000'de çalışıyorsa önce onu kapat.

### Hesaplar (giriş)

Uygulama kullanıcı adı ve şifre ister. Kayıt sayfası yok; hesaplar komut satırından
yönetilir (`backend/` klasöründe):

```powershell
.venv\Scripts\python.exe -m app.cli set-password admin   # hesaplardan önceki verinin sahibi
.venv\Scripts\python.exe -m app.cli create-user anna      # yeni hesap
.venv\Scripts\python.exe -m app.cli list-users
```

`start.ps1` şifresi olmayan bir hesap görürse hangi komutu çalıştıracağını yazar.
5 hatalı denemeden sonra giriş 15 dakika bekletilir.

### Telefondan / başka cihazdan erişim (Tailscale)

Uygulama şifreyle korunuyor, ama bu bilgisayardaki sunucu HTTP (şifresiz bağlantı) kullanıyor.
Bu yüzden internete açma; yalnızca kendi cihazlarının bağlandığı özel bir ağ üzerinden eriş.

1. [Tailscale](https://tailscale.com/download)'i bu bilgisayara ve telefonuna kur, ikisinde de
   aynı hesapla giriş yap.
2. Windows Güvenlik Duvarı'nda 8000 numaralı portu **yalnızca Tailscale ağına** aç
   (PowerShell'i yönetici olarak aç):

   ```powershell
   New-NetFirewallRule -DisplayName "Kelime Antrenoru (Tailscale)" -Direction Inbound `
     -Protocol TCP -LocalPort 8000 -RemoteAddress 100.64.0.0/10 -Action Allow
   ```

   İlk başlatmada Windows "python.exe'ye erişim izni verilsin mi?" diye sorarsa **İptal**'i
   seç. Böylece ev ağındaki diğer cihazlar erişemez; yalnızca yukarıdaki kural geçerli olur.
3. Telefonda `http://<bilgisayar-adı>:8000` adresini aç. Bilgisayar adını Tailscale
   uygulamasında görebilirsin; `tailscale ip -4` ile çıkan `100.x.y.z` adresi de çalışır.
   Ana ekrana kısayol ekleyince uygulama gibi açılır.

Bilgisayar uyku modundayken uygulamaya erişilemez. Sürekli erişim istiyorsan Windows güç
ayarlarından uykuyu kapat ya da süresini uzat.

### Oturum açınca otomatik başlatma (isteğe bağlı)

Docker Desktop'ta "Start Docker Desktop when you sign in" açık olmalı. Sonra bir kere:

```powershell
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File C:\work\spektrum\start.ps1 -SkipBuild'
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName 'Kelime Antrenoru' -Action $action -Trigger $trigger
```

Kaldırmak için: `Unregister-ScheduledTask -TaskName 'Kelime Antrenoru'`.
Kod güncellendiyse bir kere `.\start.ps1` ile (derleyerek) başlat.

### Yedekleme

Öğrenme ilerlemen PostgreSQL'de (Docker volume `backend_vocab-pgdata`), PDF'ler
`backend/uploads/` klasöründe durur.

```powershell
# Yedek al (yedek.dump bulunduğun klasöre kopyalanır)
docker exec vocab-postgres pg_dump -U vocab -Fc -f /tmp/yedek.dump vocab
docker cp vocab-postgres:/tmp/yedek.dump .\yedek.dump

# Geri yükle (mevcut verinin üzerine yazar)
docker cp .\yedek.dump vocab-postgres:/tmp/yedek.dump
docker exec vocab-postgres pg_restore -U vocab -d vocab --clean --if-exists /tmp/yedek.dump
```

`uploads/` klasörünü de ayrıca kopyala.

`docker compose down -v` volume'u siler; bütün ilerlemen gider. Kullanma.

## İnternette yayın (Fly.io + Neon)

- **Uygulama:** Fly.io, uygulama adı `spektrum-kelime`, bölge Frankfurt (`fly.toml`). Tek makine;
  boştayken durur, ilk istekte birkaç saniyede açılır. PDF'ler `uploads` volume'unda
  (1 GB, günlük snapshot, 30 gün saklanır).
- **Yapay zekâ:** Her kullanıcı kendi sağlayıcısını, modelini ve API anahtarını ⚙️ Ayarlar'dan
  girer. Anahtarlar `SECRET_KEY` secret'ıyla şifrelenir; bu secret değişirse kayıtlı anahtarlar
  okunamaz ve kullanıcıların yeniden girmesi gerekir.
- **Veritabanı:** Neon (ücretsiz plan, Frankfurt). Bağlantı adresi Fly'da `DATABASE_URL`
  secret'ı olarak durur; Neon'un kendi yedek/geri dönüş geçmişi vardır. Fly secret'ları:
  `DATABASE_URL`, `SECRET_KEY`.
- **Otomatik yayın:** `main` dalına her push'ta GitHub Actions testleri çalıştırır, sonra
  `flyctl deploy` ile yayınlar (`.github/workflows/deploy.yml`). Migration'lar yeni sürüm
  açılmadan önce çalışır; hata olursa eski sürüm yayında kalır. GitHub'daki secret:
  `FLY_API_TOKEN` (yalnızca bu uygulamaya deploy yetkisi, 1 yıl geçerli), değişken:
  `FLY_DEPLOY=true`.

Sık kullanılan komutlar (`flyctl` = `%USERPROFILE%\.fly\bin\flyctl.exe`):

```powershell
flyctl logs --app spektrum-kelime                         # canlı loglar
flyctl status --app spektrum-kelime
flyctl ssh console --app spektrum-kelime -C "python -m app.cli set-password admin"
flyctl ssh console --app spektrum-kelime -C "python -m app.cli create-user anna"
```

Deploy token'ının süresi dolunca (1 yıl) yenisini oluşturup GitHub'a koy:
`flyctl tokens create deploy --app spektrum-kelime --expiry 8760h` → GitHub → Settings →
Secrets → `FLY_API_TOKEN`.

Not: PDF analizi tek istekte ~150 sn sürer; Fly'ın proxy'si çok uzun süren istekleri kesebilir.
Gerekirse analizi arka plan işine çevirebiliriz.
