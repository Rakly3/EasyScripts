# Win_IOMMU-list.ps1
0.01
Windows PowerShell
List all the IOMMU groups
Random order


# Win_SED-status
0.01
Windows
Show Self Encryption status of Volumes

NOTE:
This does not show of the feature is or is not supported by the device.
Not all drives support SED. - Manufacturer device information also often does not list this. Ask Bing CoPilot. It knows...

- Most mechanical HDDs do not support this.
- Many/Most NVMe devices do.
- Many SSD devices don't.
- SD devices can't.

When feature is supported, it will likely require some tool to enable it. For example: 'Samsung Magician' tool.
Will also require a complete secure wiping of the drive. This can be a long slow process as you are literally writing over every single bit of storage on the drive to remove traces of old data you might want to hide. - Without secure wipe, it might still be possible to recover old data that has not been overwritten yet.
