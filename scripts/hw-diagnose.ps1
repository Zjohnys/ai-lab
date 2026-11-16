<#
.SYNOPSIS
    Prints the hardware facts that decide which local models fit on this machine.
.DESCRIPTION
    Read-only. Reports CPU, RAM, GPU/VRAM, disks and the state of Ollama.
    Run from the repository root:
        powershell -ExecutionPolicy Bypass -File scripts/hw-diagnose.ps1
#>

$ErrorActionPreference = 'Stop'

function Write-Section([string]$Title) {
    Write-Output ''
    Write-Output "== $Title =="
}

Write-Section 'CPU'
Get-CimInstance Win32_Processor |
    ForEach-Object { '{0} ({1} cores, {2} threads)' -f $_.Name.Trim(), $_.NumberOfCores, $_.NumberOfLogicalProcessors }

Write-Section 'RAM'
$os = Get-CimInstance Win32_OperatingSystem
$totalGb = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB
$freeGb = $os.FreePhysicalMemory / 1MB   # FreePhysicalMemory is reported in KB
'{0:N1} GB total, {1:N1} GB free' -f $totalGb, $freeGb
if ($freeGb -lt 3) {
    'WARNING: under 3 GB free. Close the browser and heavy apps before loading a model.'
}

Write-Section 'GPU'
# Win32_VideoController.AdapterRAM is a 32-bit field and caps at 4 GB,
# so nvidia-smi is the reliable source for VRAM on NVIDIA cards.
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $gpuRows = nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader,nounits
    foreach ($row in $gpuRows) {
        $name, $totalMb, $usedMb = $row -split ',\s*'
        $freeVramGb = ([int]$totalMb - [int]$usedMb) / 1024
        '{0}: {1:N1} GB VRAM total, {2:N1} GB in use, {3:N1} GB available for models' -f `
            $name, ([int]$totalMb / 1024), ([int]$usedMb / 1024), $freeVramGb
    }
}
else {
    Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name }
    'nvidia-smi not found: no NVIDIA GPU or driver. Models will run on CPU.'
}

Write-Section 'Disks'
Get-Volume | Where-Object DriveLetter | Sort-Object DriveLetter | ForEach-Object {
    '{0}: {1:N0} GB free of {2:N0} GB' -f $_.DriveLetter, ($_.SizeRemaining / 1GB), ($_.Size / 1GB)
}
Get-PhysicalDisk | ForEach-Object {
    '{0}: {1} over {2}' -f $_.FriendlyName, $_.MediaType, $_.BusType
}

Write-Section 'Ollama'
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    ollama --version
    try {
        $tags = Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 3
        if ($tags.models) {
            $tags.models | ForEach-Object { '{0} ({1:N1} GB)' -f $_.name, ($_.size / 1GB) }
        }
        else {
            'Server is running, but no models are installed. Try: ollama pull qwen3:8b'
        }
    }
    catch {
        'Installed, but the server is not answering on http://localhost:11434.'
    }
}
else {
    'Not installed. Install with: winget install Ollama.Ollama'
}

Write-Section 'Rule of thumb'
'A model runs fully on the GPU when its file size plus about 1 GB for context fits in the available VRAM.'
'If it does not fit, Ollama splits it between GPU and CPU and generation gets much slower.'
