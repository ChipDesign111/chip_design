param(
    [ValidateSet('doctor','collect','train','run','build','program')]
    [string]$Action = 'doctor',
    [string]$Model = 'tools/local/camera_demo/my_action_model',
    [string]$Dataset = 'tools/local/camera_demo/actions.npz',
    [string]$Build = 'tools/local/camera_demo/bitstream_new',
    [string]$Vivado = 'D:\pkuwyh\Vivado\2019.1\bin\vivado.bat',
    [int]$Camera = 0,
    [switch]$ManualCapture
)
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Push-Location $Repo
try {
    $Py = Join-Path $Repo '.venv-demo\Scripts\python.exe'
    if ($Action -in @('build','program')) {
        if (-not (Test-Path -LiteralPath $Vivado)) { throw "Vivado not found: $Vivado" }
        if ($Action -eq 'build') {
            & $Vivado -mode batch -nojournal -source fpga/demo/build_bitstream.tcl -tclargs $Build
        } else {
            if (-not (Test-Path -LiteralPath (Join-Path $Build 'build_status.txt'))) {
                throw 'Build has no passing status. Do not program a failed or stale build.'
            }
            & $Vivado -mode batch -nojournal -source fpga/demo/program_bitstream.tcl -tclargs (Join-Path $Build 'fpga_top.bit')
        }
    } else {
        if (-not (Test-Path -LiteralPath $Py)) { throw 'Run fpga/demo/setup.ps1 first' }
        switch ($Action) {
            'doctor' { & $Py -m fpga.demo.doctor }
            'collect' {
                $captureArguments = @('-m','fpga.demo.camera','collect','--camera',"$Camera",'--output',$Dataset)
                if (-not $ManualCapture) {
                    $captureArguments += @('--auto-advance','--countdown','10','--pose-timeout','120')
                }
                & $Py @captureArguments
            }
            'train' { & $Py -m fpga.demo.train_camera --dataset $Dataset --out $Model }
            'run' { & $Py -m fpga.demo.camera run --camera $Camera --package (Join-Path $Model 'resident') }
        }
    }
    if ($LASTEXITCODE -ne 0) { throw "$Action failed (exit $LASTEXITCODE)" }
} finally { Pop-Location }
