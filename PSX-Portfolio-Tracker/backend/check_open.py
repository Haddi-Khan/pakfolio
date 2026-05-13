import urllib.request, re
try:
    html = urllib.request.urlopen('https://dps.psx.com.pk/company/NPL').read().decode('utf-8')
    m = re.findall(r'<div class="stats_label">\s*Open\s*</div>\s*<div class="stats_value">\s*([\d,.]+)\s*</div>', html, re.S)
    print("Open:", m)
except Exception as e:
    print(e)
