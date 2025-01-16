Get-WmiObject Win32_PnPEntity | ForEach-Object {
    $device = $_
    $deviceID = $device.DeviceID
    $groupID = (Get-WmiObject Win32_PnPSignedDriver | Where-Object { $_.DeviceID -eq $deviceID }).DriverVersion
    Write-Host "Group: $groupID - Device: $($device.Caption) (Device ID: $deviceID)"
}
