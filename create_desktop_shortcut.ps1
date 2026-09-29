
$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\CA Trader.lnk")
$Shortcut.TargetPath = "C:\Users\SantoshMadnani\OneDrive - BDO INDIA SERVICES PRIVATE LIMITED\Personal files\CA_Trader\dist\CA_Trader\CA_Trader.exe"
$Shortcut.WorkingDirectory = "C:\Users\SantoshMadnani\OneDrive - BDO INDIA SERVICES PRIVATE LIMITED\Personal files\CA_Trader\dist\CA_Trader"
$Shortcut.IconLocation = "C:\Users\SantoshMadnani\OneDrive - BDO INDIA SERVICES PRIVATE LIMITED\Personal files\CA_Trader\dist\CA_Trader\static\ca_trader.ico, 0"
$Shortcut.Description = "CA Trader - Institutional Trading Terminal"
$Shortcut.Save()
Write-Host "Desktop shortcut created: $DesktopPath\CA Trader.lnk"
