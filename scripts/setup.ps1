# ตั้งค่าโปรเจคครั้งแรกบน Windows
#
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#
# ทำให้ครบตั้งแต่สร้าง virtual environment จนถึงรันเทสต์ผ่าน
# สคริปต์นี้ไม่เขียนทับไฟล์ backend\.env ที่มีอยู่แล้ว และไม่แตะฐานข้อมูล

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

function Step($n, $text) { Write-Host "`n[$n] $text" -ForegroundColor Cyan }
function Ok($text)       { Write-Host "    OK  $text" -ForegroundColor Green }
function Warn($text)     { Write-Host "    !   $text" -ForegroundColor Yellow }

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
& $vpy -m pip install -r backend\requirements.txt -r ml\requirements.txt -r requirements-dev.txt --quiet
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

# ------------------------------------------------------------------ 6. เทสต์
Step 6 "รันเทสต์เพื่อยืนยันว่าทุกอย่างพร้อม"
& $vpy -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nเทสต์ไม่ผ่าน - ดูข้อความข้างบนประกอบ" -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------- 7. Docker
Step 7 "ตรวจ Docker"
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker info *>$null
    if ($LASTEXITCODE -eq 0) { Ok "Docker พร้อมใช้งาน" }
    else { Warn "ติดตั้ง Docker แล้วแต่ยังไม่ได้เปิด - เปิด Docker Desktop ก่อนรันระบบ" }
} else {
    Warn "ยังไม่ได้ติดตั้ง Docker Desktop - https://www.docker.com/products/docker-desktop/"
}

Write-Host "`nพร้อมใช้งานแล้ว" -ForegroundColor Green
Write-Host @"

ขั้นต่อไป เปิด Docker Desktop แล้วสั่ง

    docker compose up -d --build

จากนั้นเปิด
    http://127.0.0.1:8000/            หน้าแรก
    http://127.0.0.1:8000/scan.html   หน้าตรวจสอบอีเมล
    http://127.0.0.1:8000/docs        เอกสาร API

อ่านรายละเอียดทั้งหมดได้ที่ docs\SETUP.md
"@
