# unnest_structure.ps1 - Streamline nested alpha_betting_system workspace

# Define paths
$rootPath = "C:\Users\Olugb\Workspace\alpha_betting_system"
$innerPath = Join-Path $rootPath "alpha_betting_system"
$backupPath = Join-Path $rootPath "backup_duplicates"
$logPath = Join-Path $rootPath "unnest_log.txt"

# Create backup folder if not exists
if (-not (Test-Path $backupPath)) {
    New-Item -ItemType Directory -Path $backupPath | Out-Null
    Write-Output "Created backup folder: $backupPath" | Out-File -FilePath $logPath -Append
}

# Function to log actions
function Log-Action {
    param ($message)
    Write-Output "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $message" | Out-File -FilePath $logPath -Append
    Write-Host $message
}

# Verify inner path exists
if (-not (Test-Path $innerPath)) {
    Log-Action "Error: Inner path $innerPath not found. Aborting."
    exit 1
}

Log-Action "Starting unnesting process..."

# Get all items in inner folder (files and subfolders)
$innerItems = Get-ChildItem -Path $innerPath -Recurse:$false  # Non-recursive to move top-level only

foreach ($item in $innerItems) {
    $targetPath = Join-Path $rootPath $item.Name
    
    if (Test-Path $targetPath) {
        # Duplicate found - backup root version and overwrite with inner
        $backupItem = Join-Path $backupPath $item.Name
        if (Test-Path $backupItem) {
            Remove-Item -Path $backupItem -Recurse -Force  # Clear existing backup
        }
        Move-Item -Path $targetPath -Destination $backupItem -Force
        Log-Action "Backed up duplicate: $targetPath to $backupItem"
        
        # Now move inner to root
        Move-Item -Path $item.FullName -Destination $targetPath -Force
        Log-Action "Overwrote duplicate with inner version: $item.Name"
    } else {
        # No duplicate - direct move
        Move-Item -Path $item.FullName -Destination $rootPath -Force
        Log-Action "Moved: $item.Name to root"
    }
}

# Remove the now-empty inner folder
if ((Get-ChildItem -Path $innerPath).Count -eq 0) {
    Remove-Item -Path $innerPath -Force
    Log-Action "Removed empty inner folder: $innerPath"
} else {
    Log-Action "Warning: Inner folder not empty after moves. Manual review needed."
}

# Post-cleanup verification
Log-Action "Verifying structure..."
$expectedItems = @('.env.example', '.gitattributes', '.gitmodules', '.gitignore', 'PROJECT_STRUCTURE.md', 'README.md', 'requirements-windows.txt', 'run.py', 'data', 'docker', 'existing_system', 'logs', 'scripts', 'src', 'tests')
$missing = @()
foreach ($exp in $expectedItems) {
    if (-not (Test-Path (Join-Path $rootPath $exp))) {
        $missing += $exp
    }
}
if ($missing.Count -eq 0) {
    Log-Action "Structure matches expected: All items present at root."
} else {
    Log-Action "Warning: Missing expected items: $($missing -join ', ')"
}

Log-Action "Unnesting complete. Review log at $logPath and backups at $backupPath if needed."