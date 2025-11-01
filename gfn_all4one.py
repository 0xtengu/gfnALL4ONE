import json
import re
from mitmproxy import http

# hosts we saw gfn hit, plus a catch-all for *.nvidiagrid.net
NVIDIA_HOSTS = (
    "play.geforcenow.com",
    "public.games.geforce.com",
    "games.geforce.com",
    "pcs.geforcenow.com",
    "mes.geforcenow.com",
    "events.gfe.nvidia.com",
    "gx-target-experiments-frontend-api.gx.nvidia.com",
    "gx-target-rconfig-frontend-api.gx.nvidia.com",
    "prod.cloudmatchbeta.nvidiagrid.net",
    "nvidiagrid.net",
)

# we just swap whatever was in (...) with windows 10 x64
UA_WIN_RE = re.compile(r"(Mozilla\/[\d\.]+) \(.+?\)")

# stuff we want the session blob to say
FAKE_WIDTH = 2560
FAKE_HEIGHT = 1440
FAKE_FPS = 120


def looksLikeNvidiaHost(host: str) -> bool:
    # just match exact or subdomain
    host = host.lower()
    for h in NVIDIA_HOSTS:
        if host == h or host.endswith("." + h):
            return True
    return False


def spoofHeaders(req: http.HTTPRequest) -> None:
    # keep headers chill and windows-y
    req.headers["nv-device-os"] = "WINDOWS"
    req.headers["sec-ch-ua-platform"] = '"Windows"'
    req.headers["sec-ch-ua-platform-version"] = "15.0.0"

    ua = req.headers.get("user-agent")
    if ua:
        # force ua to advertise windows
        req.headers["user-agent"] = UA_WIN_RE.sub(
            r'\1 (Windows NT 10.0; Win64; x64)',
            ua,
        )


def spoofQuery(req: http.HTTPRequest) -> None:
    # mitmproxy 12 gives us a multidict here, so just poke values
    q = req.query

    def set_if(name: str, value: str) -> None:
        if name in q:
            q[name] = value

    # names we actually saw in your flows
    set_if("deviceOS", "Windows_NT")
    set_if("deviceOs", "Windows_NT")
    set_if("osName", "WINDOWS")
    set_if("deviceOSVersion", "10.0")
    # if they add new params, this won’t crash because we don’t rebuild anything


def spoofJson(req: http.HTTPRequest, url: str) -> None:
    # only care about json-ish posts
    ctype = req.headers.get("content-type", "")
    if "application/json" not in ctype.lower():
        return

    try:
        data = json.loads(req.content)
    except Exception:
        # sometimes it’s empty or not json, just bail
        return

    changed = False

    # top-level os hints
    for key in ("deviceOS", "deviceOs", "osName"):
        val = data.get(key)
        if isinstance(val, str) and val.upper().startswith("LINUX"):
            data[key] = "WINDOWS"
            changed = True

    # telemetry style blob like events.gfe... we saw that in your dump :contentReference[oaicite:0]{index=0}
    device_info = data.get("deviceInfo")
    if isinstance(device_info, dict):
        os_val = device_info.get("deviceOS")
        if isinstance(os_val, str) and os_val.upper().startswith("LINUX"):
            device_info["deviceOS"] = "WINDOWS"
            device_info["deviceOSVersion"] = "10.0"
            changed = True

        # tell them we have a wide-ish window to cover ui checks
        device_info["windowInnerWidth"] = 3440
        device_info["windowInnerHeight"] = 1400
        changed = True

    # main one: session setup
    if ".nvidiagrid.net/v2/session" in url or url.endswith("/v2/session"):
        srd = data.get("sessionRequestData")
        if isinstance(srd, dict):
            # copy the gist idea: 1 monitor, big res, fast fps
            srd["clientRequestMonitorSettings"] = [
                {
                    "widthInPixels": FAKE_WIDTH,
                    "heightInPixels": FAKE_HEIGHT,
                    "framesPerSecond": FAKE_FPS,
                }
            ]
            # sometimes they stash os info here too
            srd["deviceOS"] = "Windows_NT"
            srd["deviceOSVersion"] = "10.0"
            changed = True

    if changed:
        req.content = json.dumps(data).encode("utf-8")


def request(flow: http.HTTPFlow) -> None:
    host = flow.request.host
    if not looksLikeNvidiaHost(host):
        return

    # 1) always spoof headers
    spoofHeaders(flow.request)

    # 2) update query in-place
    spoofQuery(flow.request)

    # 3) maybe patch json body
    #    (only matters for /v2/session and telemetry posts)
    spoofJson(flow.request, flow.request.pretty_url)

