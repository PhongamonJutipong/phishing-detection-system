# ตั้งค่าและเริ่มระบบด้วยคำสั่งเดียวบน Windows
#
#   scripts\setup.bat              <- วิธีที่ง่ายที่สุด
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 [-SkipRun]
#
# ทำให้ครบตั้งแต่สร้าง virtual environment ไปจนถึงระบบรันอยู่และเปิดหน้าเว็บให้
# ใส่ -SkipRun ถ้าต้องการติดตั้งอย่างเดียวโดยไม่เริ่มระบบ
#
# รันซ้ำได้ปลอดภัย ไม่เขียนทับ .venv, backend\.env หรือโมเดลที่มีอยู่แล้ว
# และไม่แตะข้อมูลในฐานข้อมูล
param(
    [switch]$SkipRun
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

function Step($n, $text) { Write-Host "`n[$n] $text" -ForegroundColor Cyan }
function Ok($text)       { Write-Host "    OK  $text" -ForegroundColor Green }
function Warn($text)     { Write-Host "    !   $text" -ForegroundColor Yellow }

# ตรวจว่า Docker daemon พร้อมหรือยัง
#
# ต้องปิด ErrorActionPreference ชั่วคราว เพราะ PowerShell ถือว่าข้อความที่โปรแกรมภายนอก
# เขียนลง stderr เป็น error เมื่อมีการ redirect ทำให้สคริปต์หยุดทั้งที่เราแค่ต้องการรู้ว่า
# Docker เปิดอยู่ไหม ซึ่งเป็นกรณีปกติที่ต้องจัดการต่อ ไม่ใช่ความผิดพลาดที่ต้องหยุด
function Test-DockerReady {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        docker info 2>&1 | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $previous
    }
}

Write-Host "ตั้งค่าโปรเจค PhishMail" -ForegroundColor White
Write-Host "โฟลเดอร์: $repo"

# ---------------------------------------------------------------- 1. Python
Step 1 "ตรวจหา Python 3.11"
$py = $null
foreach ($cand in @("py -3.11", "python3.11", "python")) {
    $exe, $arg = $cand.Split(" ", 2)
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
    try {
        $v = if ($arg) { & $exe $arg --version 2>$null } else { & $exe --version 2>$null }
    } catch { continue }
    if ($v -match "Python 3\.(\d+)") {
        if ([int]$Matches[1] -eq 11) { $py = $cand; Ok "$v ($cand)"; break }
        Warn "$v ที่ $cand - โปรเจคนี้ทดสอบกับ 3.11"
    }
}
if (-not $py) {
    Write-Host "`nไม่พบ Python 3.11 - ติดตั้งจาก https://www.python.org/downloads/release/python-3119/" -ForegroundColor Red
    Write-Host "ตอนติดตั้งให้ติ๊ก 'Add python.exe to PATH' ด้วย" -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------- 2. virtual environment
Step 2 "สร้าง virtual environment (.venv)"
if (Test-Path ".venv\Scripts\python.exe") {
    Ok "มีอยู่แล้ว ข้ามขั้นตอนนี้"
} else {
    $exe, $arg = $py.Split(" ", 2)
    if ($arg) { & $exe $arg -m venv .venv } else { & $exe -m venv .venv }
    Ok "สร้างแล้ว"
}
$vpy = Join-Path $repo ".venv\Scripts\python.exe"

# ------------------------------------------------------------ 3. dependencies
Step 3 "ติดตั้ง dependencies (ใช้เวลาสักครู่)"
& $vpy -m pip install --upgrade pip --quiet
# ติดตั้งแบบ editable จาก pyproject.toml ซึ่งเป็นแหล่งข้อมูล dependencies เพียงแหล่งเดียว
#   .[ml]  = pandas/openpyxl สำหรับเตรียมข้อมูล   .[dev] = pytest/httpx สำหรับเทสต์
& $vpy -m pip install -e ".[ml,dev]" --quiet
if ($LASTEXITCODE -ne 0) { throw "ติดตั้ง dependencies ไม่สำเร็จ" }
Ok "ติดตั้งครบแล้ว"

# ------------------------------------------------------------------- 4. .env
Step 4 "สร้างไฟล์ตั้งค่า backend\.env"
if (Test-Path "backend\.env") {
    Ok "มีอยู่แล้ว ไม่เขียนทับ"
} else {
    Copy-Item "backend\.env.example" "backend\.env"

    # สร้างกุญแจเข้ารหัสและ token ผู้ดูแลแบบสุ่ม ไม่ให้ใครต้องมานั่งสร้างเอง
    $key   = & $vpy -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    $token = & $vpy -c "import secrets; print(secrets.token_urlsafe(24))"
    $pepper= & $vpy -c "import secrets; print(secrets.token_urlsafe(32))"

    $env_text = Get-Content "backend\.env" -Raw
    $env_text = $env_text -replace "(?m)^ENCRYPTION_KEY=.*$", "ENCRYPTION_KEY=$key"
    $env_text = $env_text -replace "(?m)^ADMIN_TOKEN=.*$",    "ADMIN_TOKEN=$token"
    $env_text = $env_text -replace "(?m)^HASH_PEPPER=.*$",    "HASH_PEPPER=$pepper"
    Set-Content "backend\.env" $env_text -Encoding utf8 -NoNewline

    Ok "สร้างแล้ว พร้อมกุญแจเข้ารหัสและ admin token แบบสุ่ม"
    Warn "ไฟล์นี้มีความลับ อยู่ใน .gitignore แล้ว อย่านำขึ้น git"
}

# ----------------------------------------------------------------- 5. โมเดล
Step 5 "เทรนโมเดล (ไฟล์ .pkl ไม่ได้อยู่ใน git จึงต้องสร้างเอง)"
if ((Test-Path "backend\ml_model\en\naive_bayes_model.pkl") -and
    (Test-Path "backend\ml_model\th\naive_bayes_model.pkl")) {
    Ok "มีโมเดลอยู่แล้ว ข้ามขั้นตอนนี้"
} else {
    Push-Location ml
    try {
        & $vpy preprocess.py --include-mock
        if ($LASTEXITCODE -ne 0) { throw "preprocess.py ไม่สำเร็จ" }
        & $vpy train.py
        if ($LASTEXITCODE -ne 0) { throw "train.py ไม่สำเร็จ" }
    } finally { Pop-Location }
    Ok "เทรนเสร็จ ได้โมเดลภาษาอังกฤษและภาษาไทย"
    Warn "โมเดลนี้เทรนจากชุดข้อมูลจำลอง ใช้ทดสอบระบบเท่านั้น ห้ามนำค่าความแม่นยำไปรายงาน"
}

# ------------------------------------------------------------ 6. หน้าเว็บ
Step 6 "ติดตั้งและ build หน้าเว็บ Angular"
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Warn "ยังไม่ได้ติดตั้ง Node.js - https://nodejs.org/ (ต้องการเวอร์ชัน 20 ขึ้นไป)"
    Warn "ติดตั้งแล้วรันสคริปต์นี้ซ้ำ ระบบจะให้บริการเฉพาะ API จนกว่าจะ build หน้าเว็บ"
} else {
    Push-Location frontend
    try {
        if (Test-Path "node_modules/.bin/ng.cmd") {
            Ok "ติดตั้ง dependencies ไว้แล้ว ข้ามขั้นตอนนี้"
        } else {
            # npm ci ใช้ package-lock.json ตรง ๆ จึงได้เวอร์ชันเดิมทุกครั้ง
            npm ci
            if ($LASTEXITCODE -ne 0) { throw "ติดตั้ง dependencies ของหน้าเว็บไม่สำเร็จ" }
        }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "build หน้าเว็บไม่สำเร็จ" }
    } finally { Pop-Location }
    Ok "build หน้าเว็บเสร็จ (ผลลัพธ์อยู่ที่ backend/app/web)"
}

# ------------------------------------------------------------------ 7. เทสต์
Step 7 "รันเทสต์เพื่อยืนยันว่าทุกอย่างพร้อม"
& $vpy -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nเทสต์ไม่ผ่าน - ดูข้อความข้างบนประกอบ" -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------- 8. Docker
Step 8 "ตรวจ Docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Warn "ยังไม่ได้ติดตั้ง Docker Desktop - https://www.docker.com/products/docker-desktop/"
    Warn "ติดตั้งแล้วรันสคริปต์นี้ซ้ำอีกครั้ง ส่วนที่ทำไปแล้วจะถูกข้าม"
    exit 0
}

if (-not (Test-DockerReady)) {
    Warn "Docker Desktop ยังไม่ได้เปิด - กำลังพยายามเปิดให้..."
    # หาตัวโปรแกรมจากตำแหน่งของ docker.exe แทนการเดา path ติดตั้ง
    # เพราะ Docker Desktop รุ่นใหม่ติดตั้งลง AppData ของผู้ใช้ ไม่ใช่ Program Files เสมอไป
    # โครงสร้างคือ <ราก>/resources/bin/docker.exe จึงถอยขึ้นสามชั้นเพื่อหา "Docker Desktop.exe"
    $dd = $null
    $dockerExe = (Get-Command docker -ErrorAction SilentlyContinue).Source
    if ($dockerExe) {
        $candidate = Join-Path (Split-Path (Split-Path (Split-Path $dockerExe))) "Docker Desktop.exe"
        if (Test-Path $candidate) { $dd = $candidate }
    }
    if (-not $dd) {
        foreach ($guess in @("$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
                             "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe")) {
            if (Test-Path $guess) { $dd = $guess; break }
        }
    }
    if ($dd) { Start-Process $dd } else { Warn "หาตัวโปรแกรมไม่เจอ กรุณาเปิด Docker Desktop ด้วยตนเอง" }

    Write-Host "    รอจนกว่า Docker จะพร้อม (สูงสุด 3 นาที)..." -NoNewline
    $deadline = (Get-Date).AddMinutes(3)
    $dockerReady = $false
    while ((Get-Date) -lt $deadline) {
        if (Test-DockerReady) { $dockerReady = $true; break }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 5
    }
    Write-Host ""
    if (-not $dockerReady) {
        Write-Host "`nDocker ยังไม่พร้อม - เปิด Docker Desktop เองแล้วสั่ง 'docker compose up -d --build'" -ForegroundColor Red
        exit 1
    }
}
Ok "Docker พร้อมใช้งาน"

if ($SkipRun) {
    Write-Host "`nติดตั้งเสร็จแล้ว (ข้ามการรันระบบตามที่สั่ง)" -ForegroundColor Green
    Write-Host "สั่ง 'docker compose up -d --build' เมื่อพร้อมใช้งาน"
    exit 0
}

# --------------------------------------------------------------- 9. รันระบบ
Step 9 "สร้าง image และเริ่มระบบ (ครั้งแรกใช้เวลาหลายนาที)"
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw "เริ่มระบบไม่สำเร็จ ดูข้อความข้างบนประกอบ" }

# ------------------------------------------------------------ 10. ตรวจว่าใช้ได้
Step 10 "รอให้ระบบพร้อมรับคำขอ"
$ready = $false
$deadline = (Get-Date).AddMinutes(3)
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 5
        if ($r.status -eq "ok") { $ready = $true; break }
    } catch { }
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 5
}
Write-Host ""

if (-not $ready) {
    Write-Host "`nระบบยังไม่ตอบกลับ - ดู log ด้วย 'docker compose logs backend'" -ForegroundColor Red
    exit 1
}
Ok "ระบบพร้อมใช้งาน (โมเดลโหลดแล้ว ฐานข้อมูลเชื่อมต่อได้)"

Write-Host "`nติดตั้งเสร็จสมบูรณ์" -ForegroundColor Green
Write-Host @"

เปิดใช้งานได้ที่
    http://127.0.0.1:8000/            หน้าแรก
    http://127.0.0.1:8000/scan.html   หน้าตรวจสอบอีเมล
    http://127.0.0.1:8000/docs        เอกสาร API

คำสั่งที่ใช้บ่อย
    docker compose logs -f backend    ดู log
    docker compose stop               หยุดชั่วคราว ข้อมูลอยู่ครบ
    docker compose down               ลบคอนเทนเนอร์ ข้อมูลยังอยู่

อ่านรายละเอียดทั้งหมดได้ที่ docs\SETUP.md
"@
Start-Process "http://127.0.0.1:8000/scan.html"
