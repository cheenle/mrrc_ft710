# FTDI Windows Runtime Files

This directory is for Windows FTDI runtime files used by the MRRC FT-710
desktop package.

Expected files:

- `bin/x64/FT4222.dll`
- `bin/x64/ftd2xx.dll`

Official sources:

- LibFT4222: `https://ftdichip.com/software-examples/ft4222h-software-examples/`
- Expected archive: `LibFT4222-v1.4.8.zip`
- D2XX: `https://ftdichip.com/drivers/d2xx-drivers/`
- Expected archive: `CDM-v2.12.36.20-WHQL-Certified.zip`

The FTDI site may return HTTP 403 to automated direct downloads. If that
happens, download the ZIP files in a browser and place them in `downloads/`,
or extract the DLLs manually into `bin/x64/`.

You can try the helper from PowerShell:

```powershell
vendor\ftdi\windows\fetch-ftdi.ps1
```

If it is blocked by the FTDI site, use the printed URLs in a browser.

Before distributing an installer, update the project license/notice file with
the applicable FTDI redistribution terms.
