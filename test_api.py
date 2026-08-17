import urllib.request, urllib.error, json
req = urllib.request.Request('https://irctc1.p.rapidapi.com/api/v1/liveTrainStatus?trainNo=12301&startDay=0', headers={'x-rapidapi-key': 'rg_955e151f5aa84f6ebe1c70f9c36ecb33', 'x-rapidapi-host': 'irctc1.p.rapidapi.com'})
try:
    print(urllib.request.urlopen(req).read().decode())
except urllib.error.HTTPError as e:
    print(e.code, e.reason)
