param(
    [ValidateSet('doctor','collect','collect-features','analyze-video','train','run','build','program')]
    [string]$Action = 'doctor',
    [string]$Model = 'tools/local/camera_demo/my_action_model',
    [string]$Dataset = 'tools/local/camera_demo/actions.npz',
    [string]$VideoDir = 'tools/local/camera_demo/video_capture',
    [string]$Build = 'tools/local/camera_demo/bitstream_new',
    [string]$Vivado = 'D:\pkuwyh\Vivado\2019.1\bin\vivado.bat',
    [int]$Camera = 0,
    [ValidateSet('full','knees')]
    [string]$FeatureProfile = 'knees',
    [switch]$ManualCapture,
    [switch]$AutoCapture,
    [switch]$Attach
)
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Push-Location $Repo
try {
    if ($ManualCapture -and $AutoCapture) { throw 'Choose manual capture or automatic capture, not both' }
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
                & $Py -m fpga.demo.record_video --camera $Camera --camera-backend auto `
                    --width 1280 --height 720 --zoom 100 --rounds 3 --output-dir $VideoDir
            }
            'analyze-video' {
                & $Py -m fpga.demo.analyze_video --manifest (Join-Path $VideoDir 'manifest.json') --output $Dataset
            }
            'collect-features' {
                $captureArguments = @('-m','fpga.demo.camera','collect','--camera',"$Camera",'--camera-backend','auto',
                    '--width','1280','--height','720','--zoom','100','--countdown','10',
                    '--feature-profile',$FeatureProfile,'--output',$Dataset)
                if ($AutoCapture) {
                    $captureArguments += @('--auto-advance','--pose-timeout','120')
                }
                & $Py @captureArguments
            }
            'train' { & $Py -m fpga.demo.train_camera --dataset $Dataset --out $Model }
            'run' {
                $ReuseResident = $Attach.IsPresent
                $ActiveModel = Join-Path $Repo 'tools/local/camera_demo/ACTIVE_CAMERA_MODEL.json'
                if (-not $PSBoundParameters.ContainsKey('Model') -and (Test-Path -LiteralPath $ActiveModel)) {
                    $SelectedModel = Get-Content -LiteralPath $ActiveModel -Raw | ConvertFrom-Json
                    $Model = $SelectedModel.model_dir
                    $ReuseResident = $ReuseResident -or ($SelectedModel.board_loaded -eq $true)
                }
                $RunArguments = @('-m','fpga.demo.camera','run','--camera',"$Camera",'--camera-backend','auto',
                    '--width','1280','--height','720','--zoom','100','--package',(Join-Path $Model 'resident'))
                if ($ReuseResident) { $RunArguments += '--attach' }
                & $Py @RunArguments
            }
        }
    }
    if ($LASTEXITCODE -ne 0) { throw "$Action failed (exit $LASTEXITCODE)" }
} finally { Pop-Location }
