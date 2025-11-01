    ██████╗ ███████╗███╗   ██╗     █████╗ ██╗     ██╗██╗  ██╗ ██████╗ ███╗   ██╗███████╗
    ██╔════╝ ██╔════╝████╗  ██║    ██╔══██╗██║     ██║██║  ██║██╔═══██╗████╗  ██║██╔════╝
    ██║  ███╗█████╗  ██╔██╗ ██║    ███████║██║     ██║███████║██║   ██║██╔██╗ ██║█████╗  
    ██║   ██║██╔══╝  ██║╚██╗██║    ██╔══██║██║     ██║╚════██║██║   ██║██║╚██╗██║██╔══╝  
    ╚██████╔╝██║     ██║ ╚████║    ██║  ██║███████╗███████╗ ██║╚██████╔╝██║ ╚████║███████╗
     ╚═════╝ ╚═╝     ╚═╝  ╚═══╝    ╚═╝  ╚═╝╚══════╝╚══════╝ ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝

                   make GeForce NOW on linux look like windows
                        unlock larger streaming resolutions
                              tiny. one script. kiss.

> [!IMPORTANT]
> GFN/NVIDIA can change server logic at any time and break this


## 0x00 What it does

- Watches only NVIDIA / GFN hosts seen in traffic
- Rewrites headers so the client presents as Windows desktop
- Edits query params in-place (no URL rebuild)
- Patches `*.nvidiagrid.net/v2/session` to inject:
>
  ```json
  {
    "clientRequestMonitorSettings": {
      "width": 2560,
      "height": 1440,
      "refreshRateHz": 120
    }
  }
  ```
> [!TIP]
> You can change the injected monitor to any value your GFN path actually accepts:
> edit `FAKE_WIDTH`, `FAKE_HEIGHT`, and `FAKE_FPS` at the top of `gfn_all4one.py`.
> Not all browser paths accept ultrawide (e.g. 3440×1440); 2560×1440 is a practical ceiling.



## 0x01 Files
```text
gfn_all4one.py                # addon (single file)
~/.mitmproxy/mitmproxy-ca.pem # mitmproxy CA (auto-generated)
```

## 0x02 Requirements
- mitmproxy / mitmdump (tested on 12.2.0)
- Google Chrome (flatpak or system)
- mitmproxy CA imported into browser trust DB
- browser using HTTP(S) proxy, tested with `127.0.0.1:8080`

> [!WARNING]
> This only works if HTTPS interception works. If you can’t or won’t trust the local CA, stop here.



## 0x03 Setup (flatpak Chrome)

```sh
# create NSS DB (if missing)
mkdir -p ~/.pki/nssdb
certutil -d sql:$HOME/.pki/nssdb -N

# import mitmproxy CA
certutil -d sql:$HOME/.pki/nssdb   -A -t "C,," -n mitmproxy   -i "$HOME/.mitmproxy/mitmproxy-ca.pem"

# allow flatpak chrome to access cert database
flatpak override --user com.google.Chrome --filesystem=$HOME/.pki/nssdb
```
> [!NOTE]
> For system Chrome, import `~/.mitmproxy/mitmproxy-ca.pem` into your OS / browser trust store instead.


Restart Chrome


## 0x04 Run & launch

```sh
cd ~/path/to/gfn-all4one
mitmdump -s gfn_all4one.py
# listens on 127.0.0.1:8080 by default
```

**flatpak:**
```sh
flatpak run com.google.Chrome   --proxy-server="http://127.0.0.1:8080"   --proxy-bypass-list=""   https://play.geforcenow.com
```

**system:**
```sh
google-chrome   --proxy-server="http://127.0.0.1:8080"   --proxy-bypass-list=""   https://play.geforcenow.com
```

> [!IMPORTANT]
> `--proxy-bypass-list=""` is required. If Chrome bypasses the proxy, you won’t see `/v2/session` and nothing gets patched.

## 0x05 Troubleshooting
If you don’t see /v2/session in mitmdump, the addon did not run

- Handshake failed / net_error -202 -> browser doesn’t trust the mitm CA. Re-import, restart
- MultiDictView object has no attribute decode -> wrong/old script; use the in-place query editing version
- Still only 1920×1200 -> confirm the intercepted /v2/session body actually contains clientRequestMonitorSettings


## 0x06 License

> [!WARNING]
> Use responsibly.  
> This project is licensed under the MIT License.  
> The author takes no liability for misuse, damage, or unintended consequences.
