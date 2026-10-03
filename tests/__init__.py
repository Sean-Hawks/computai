import os

# 測試不連網查新版
os.environ["COMPUTAI_NO_UPDATE_CHECK"] = "1"
os.environ["COMPUTAI_TAILSCALE"] = "none"
