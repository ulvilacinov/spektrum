# Almanca Kelime Antrenörü

Almanca → Türkçe kelime öğrenme uygulaması: PDF yükle, AI bölümleri ve kelimeleri çıkarsın,
kelimeleri gruplar hâlinde öğren, quiz'le pekiştir, zayıf kelimeleri tekrar et.

- `backend/` — FastAPI + PostgreSQL + Gemini ([backend/README.md](backend/README.md))
- `frontend/` — React arayüzü ([frontend/README.md](frontend/README.md))
- `docs/SPEC.md` — ürün tanımı
- `deploy/` — AWS kurulumu ve otomatik yayın ([deploy/README.md](deploy/README.md))

## Kendi bilgisayarında çalıştırma

Gerekenler (bir kere): Docker Desktop, Python 3.12, Node.js 20+ ve `backend/.env`
(`backend/.env.example` dosyasını kopyalayıp `GEMINI_API_KEY` gir). Backend'in sanal ortamı
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
