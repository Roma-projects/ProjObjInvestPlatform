param(
    [switch]$Rotate
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw 'PowerShell 7 or newer is required to generate the RSA signing key.'
}

$envPath = Join-Path (Split-Path -Parent $PSScriptRoot) '.env'
$examplePath = Join-Path (Split-Path -Parent $PSScriptRoot) '.env.example'
if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath $examplePath -Destination $envPath
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.AddRange([string[]](Get-Content -LiteralPath $envPath))
$secretNames = @(
    'POSTGRES_PASSWORD', 'RABBITMQ_DEFAULT_PASS', 'AUTH_DB_PASSWORD',
    'LISTING_DB_PASSWORD', 'MODERATION_DB_PASSWORD', 'ANALYTIC_AI_DB_PASSWORD',
    'AUTH_GATEWAY_SECRET', 'LISTING_GATEWAY_SECRET', 'SEARCH_GATEWAY_SECRET',
    'MODERATION_GATEWAY_SECRET', 'MESSAGING_GATEWAY_SECRET', 'NOTIFICATION_GATEWAY_SECRET',
    'AUTH_MODERATION_SECRET', 'LISTING_MODERATION_SECRET', 'MONGO_ROOT_PASSWORD',
    'SEARCH_MONGO_PASSWORD', 'ANALYTIC_SCRIPTS_MONGO_PASSWORD', 'PARSERS_MONGO_PASSWORD',
    'MESSAGING_MONGO_PASSWORD', 'NOTIFICATION_MONGO_PASSWORD', 'GATEWAY_REDIS_PASSWORD',
    'AUTH_REDIS_PASSWORD', 'SEARCH_REDIS_PASSWORD', 'ANALYTIC_AI_REDIS_PASSWORD'
)
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
    foreach ($name in $secretNames) {
        $pattern = '^' + [regex]::Escape($name) + '='
        $foundIndexes = @()
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match $pattern) { $foundIndexes += $i }
        }
        if ($foundIndexes.Count -gt 1) {
            throw "Duplicate $name entries in $envPath; remove duplicates before generating secrets."
        }
        $index = if ($foundIndexes.Count -eq 1) { $foundIndexes[0] } else { -1 }
        if (-not $Rotate -and $index -ge 0 -and $lines[$index] -notmatch '=(replace-with|change-this-password)(-|$)') { continue }

        $bytes = [byte[]]::new(36)
        $rng.GetBytes($bytes)
        $value = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
        if ($index -ge 0) { $lines[$index] = "$name=$value" } else { $lines.Add("$name=$value") }
    }
} finally {
    $rng.Dispose()
}

$privateKeyLine = -1
$publicKeyLine = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^JWT_PRIVATE_KEY_B64=') { $privateKeyLine = $i }
    if ($lines[$i] -match '^JWT_PUBLIC_KEY_B64=') { $publicKeyLine = $i }
}
$privateKeyNeedsGeneration = $Rotate -or $privateKeyLine -lt 0 -or $lines[$privateKeyLine] -match '=replace-with'
$publicKeyNeedsGeneration = $Rotate -or $publicKeyLine -lt 0 -or $lines[$publicKeyLine] -match '=replace-with'
if (-not $Rotate -and $privateKeyNeedsGeneration -ne $publicKeyNeedsGeneration) {
    throw 'JWT RSA key pair is incomplete. Supply both keys or use -Rotate to generate a new matching pair.'
}
if ($privateKeyNeedsGeneration -or $publicKeyNeedsGeneration) {
    $rsa = [System.Security.Cryptography.RSA]::Create(3072)
    try {
        $privateDer = [Convert]::ToBase64String($rsa.ExportPkcs8PrivateKey())
        $publicDer = [Convert]::ToBase64String($rsa.ExportSubjectPublicKeyInfo())
        $privateBody = ($privateDer -split '(.{64})' | Where-Object { $_ }) -join "`n"
        $publicBody = ($publicDer -split '(.{64})' | Where-Object { $_ }) -join "`n"
        $privatePem = "-----BEGIN PRIVATE KEY-----`n${privateBody}`n-----END PRIVATE KEY-----`n"
        $publicPem = "-----BEGIN PUBLIC KEY-----`n${publicBody}`n-----END PUBLIC KEY-----`n"
        $privateKey = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($privatePem))
        $publicKey = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($publicPem))
    } finally {
        $rsa.Dispose()
    }
    if ($privateKeyLine -ge 0) { $lines[$privateKeyLine] = "JWT_PRIVATE_KEY_B64=$privateKey" } else { $lines.Add("JWT_PRIVATE_KEY_B64=$privateKey") }
    if ($publicKeyLine -ge 0) { $lines[$publicKeyLine] = "JWT_PUBLIC_KEY_B64=$publicKey" } else { $lines.Add("JWT_PUBLIC_KEY_B64=$publicKey") }
}

# Remove the retired HS256 signing secret so it cannot be mistaken for an active setting.
$lines = [System.Collections.Generic.List[string]]::new([string[]]@($lines | Where-Object { $_ -notmatch '^JWT_SECRET_KEY=' }))

if (-not ($lines | Where-Object { $_ -match '^MONGO_ROOT_USERNAME=' })) {
    $lines.Add('MONGO_ROOT_USERNAME=miero_admin')
}
$userLine = $lines | Where-Object { $_ -match '^RABBITMQ_DEFAULT_USER=' } | Select-Object -First 1
$passLine = $lines | Where-Object { $_ -match '^RABBITMQ_DEFAULT_PASS=' } | Select-Object -First 1
$rabbitUrlIndex = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^RABBITMQ_URL_DOCKER=') { $rabbitUrlIndex = $i; break }
}
if ($userLine -and $passLine -and ($Rotate -or $rabbitUrlIndex -lt 0 -or $lines[$rabbitUrlIndex] -match 'replace-with')) {
    $rabbitUser = ($userLine -split '=', 2)[1]
    $rabbitPassword = ($passLine -split '=', 2)[1]
    $scheme = 'amqp://'
    $authority = 'rabbitmq:5672'
    $virtualHost = '/'
    if ($rabbitUrlIndex -ge 0 -and $lines[$rabbitUrlIndex] -match '^RABBITMQ_URL_DOCKER=(amqps?://)(?:[^/@]+@)?([^/]+)(/.*)?$') {
        $scheme = $Matches[1]
        $authority = $Matches[2]
        if ($Matches[3]) { $virtualHost = $Matches[3] }
    }
    $escapedUser = [uri]::EscapeDataString($rabbitUser)
    $escapedPassword = [uri]::EscapeDataString($rabbitPassword)
    $rabbitUrl = "RABBITMQ_URL_DOCKER=${scheme}${escapedUser}:${escapedPassword}@${authority}${virtualHost}"
    if ($rabbitUrlIndex -ge 0) { $lines[$rabbitUrlIndex] = $rabbitUrl } else { $lines.Add($rabbitUrl) }
}

$encoding = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllLines($envPath, $lines, $encoding)
if ($IsWindows) {
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    & icacls.exe $envPath /inheritance:r /grant:r "${currentUser}:(F)" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not restrict .env permissions for $currentUser."
    }
}
if ($Rotate) {
    Write-Warning 'Secrets were rotated in .env. Update existing datastore credentials in a coordinated maintenance window before restarting services.'
    Write-Output 'Rotated generated application secrets in .env.'
} else {
    Write-Output 'Generated missing local application secrets in .env; existing non-placeholder values were preserved.'
}
