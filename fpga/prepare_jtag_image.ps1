param(
    [Parameter(Mandatory = $true)]
    [string]$InputHex,

    [string]$OutputBin
)

$ErrorActionPreference = "Stop"
$source = (Resolve-Path -LiteralPath $InputHex).Path

if (-not $OutputBin) {
    $OutputBin = [IO.Path]::ChangeExtension($source, ".bin")
}

$tokens = @(
    Get-Content -LiteralPath $source |
        ForEach-Object { $_.Split("#", 2)[0].Trim() } |
        Where-Object { $_ } |
        ForEach-Object { $_ -split "\s+" }
)

if ($tokens.Count -ne 2048) {
    throw "Expected 2048 32-bit words, found $($tokens.Count)"
}

$bytes = [byte[]]::new(8192)
for ($index = 0; $index -lt $tokens.Count; $index++) {
    $text = $tokens[$index]
    if ($text -notmatch '^[0-9A-Fa-f]{1,8}$') {
        throw "Invalid hex word at index $index`: $text"
    }

    [uint32]$value = [Convert]::ToUInt32($text, 16)
    $offset = 4 * $index
    $bytes[$offset] = [byte](($value -shr 0) -band 0xff)
    $bytes[$offset + 1] = [byte](($value -shr 8) -band 0xff)
    $bytes[$offset + 2] = [byte](($value -shr 16) -band 0xff)
    $bytes[$offset + 3] = [byte](($value -shr 24) -band 0xff)
}

$output = [IO.Path]::GetFullPath($OutputBin)
[IO.File]::WriteAllBytes($output, $bytes)

$hash = (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash
Write-Output "Created $output"
Write-Output "Words: 2048; bytes: 8192; SHA-256: $hash"
