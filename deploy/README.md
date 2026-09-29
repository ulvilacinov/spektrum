# AWS'ye kurulum

Tek bir EC2 sunucusu üzerinde Docker Compose: PostgreSQL + uygulama + Caddy (otomatik HTTPS).
`main` dalına her push'ta GitHub Actions testleri çalıştırır, Docker imajını GHCR'ye yükler ve
sunucuyu günceller. Veritabanı ve PDF'ler her gece 03:00'te (UTC) S3'e yedeklenir.

Adres: `https://<ip-tireli>.sslip.io` (ör. `3-120-45-67.sslip.io`). Alan adı almaya gerek yok;
sertifikayı Caddy Let's Encrypt'ten kendisi alır.

**Aylık maliyet (Frankfurt, yaklaşık):** t3.small ~17 $ + 20 GB disk ~2 $ + sabit IP ~4 $ +
S3 yedekleri <1 $ ≈ **23 $**.

## 1. AWS konsolunda yapılacaklar (bir kere)

Sağ üstten bölge olarak **Europe (Frankfurt) eu-central-1** seç; hepsini aynı bölgede yap.

### a) SSH anahtarı

EC2 → **Key pairs** → **Create key pair**
- Name: `spektrum-deploy`, Key pair type: **ED25519**, Private key file format: **.pem**
- İnen `spektrum-deploy.pem` dosyasını sakla (ör. `C:\Users\<sen>\.ssh\`). Kaybolursa yenisi gerekir.

### b) Yedekler için S3 bucket

S3 → **Create bucket**
- Bucket name: `spektrum-backups-<rastgele>` (dünya genelinde benzersiz olmalı, ör. `spektrum-backups-ulvi-2026`)
- Region: Frankfurt · **Block all public access: açık kalsın** (varsayılan) → Create
- Bucket'ı aç → **Management** → **Create lifecycle rule**: ad `30-gun`, "Apply to all objects",
  "Expire current versions of objects" → **30** gün → Create

### c) Sunucunun S3'e yazabilmesi için IAM rolü

IAM → **Roles** → **Create role**
- Trusted entity: **AWS service**, Use case: **EC2** → Next → (izin seçmeden) Next
- Role name: `spektrum-ec2` → Create role
- Rolü aç → **Add permissions → Create inline policy** → **JSON** sekmesine şunu yapıştır
  (bucket adını değiştir) → policy adı `spektrum-backups` → Create:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::spektrum-backups-BURAYA-BUCKET-ADI/*"
    }
  ]
}
```

### d) Sunucu

EC2 → **Launch instance**
- Name: `spektrum`
- AMI: **Ubuntu Server 24.04 LTS**, Architecture **64-bit (x86)**
- Instance type: **t3.small**
- Key pair: `spektrum-deploy`
- Network settings → **Edit** → "Create security group", üç kural:
  - SSH (22), Source: **Anywhere 0.0.0.0/0**. GitHub Actions'ın bağlanabilmesi için gerekli;
    giriş yalnızca `.pem` anahtarıyla olur (şifreyle SSH kapalıdır).
  - HTTP (80), Source: Anywhere (sertifika için ve HTTPS'ye yönlendirme)
  - HTTPS (443), Source: Anywhere
- Configure storage: **20 GiB gp3**
- **Advanced details**:
  - IAM instance profile: `spektrum-ec2`
  - User data: [`ec2-user-data.sh`](ec2-user-data.sh) dosyasının içeriğinin tamamını yapıştır
    (Docker, AWS CLI ve swap'ı kurar)
- **Launch instance**

### e) Sabit IP

EC2 → **Elastic IPs** → **Allocate Elastic IP address** → Allocate → seç →
**Actions → Associate Elastic IP address** → Instance: `spektrum` → Associate.
Bu IP adresini not al (sunucu yeniden başlasa da değişmez; sslip adresi buna bağlı).

## 2. Bana ilet

1. Elastic IP adresi
2. `.pem` dosyasının bilgisayardaki yolu
3. S3 bucket adı

Gerisini ben yaparım:
- GitHub'a secret'ları ekler (`EC2_HOST`, `EC2_SSH_KEY`, `GEMINI_API_KEY`, üretilmiş
  `POSTGRES_PASSWORD`) ve değişkenleri ayarlarım (`BACKUP_BUCKET`, `DEPLOY_ENABLED=true`)
- İlk deploy'u başlatırım
- Yerel veritabanını ve PDF'leri sunucuya taşırım
- `admin` şifreni sunucuda belirleriz

## Sonrası

- Her `main` push'u otomatik yayınlanır (GitHub → Actions sekmesinden izlenir).
- Sunucuya bağlanmak: `ssh -i spektrum-deploy.pem ubuntu@<ip>`, sonra `cd /opt/spektrum`.
- Hesap işlemleri sunucuda:
  `docker compose exec app python -m app.cli set-password admin`
- Loglar: `docker compose logs -f app`
- Yedekten geri yükleme: dump dosyasını S3 konsolundan indir (sunucunun rolü yalnızca yazabilir,
  bir saldırgan yedekleri okuyamasın diye), sunucuya kopyala ve yükle:
  ```bash
  scp -i spektrum-deploy.pem vocab-<tarih>.dump ubuntu@<ip>:/tmp/restore.dump
  # sunucuda (/opt/spektrum):
  docker compose exec -T postgres pg_restore -U vocab -d vocab --clean --if-exists < /tmp/restore.dump
  ```
