import requests


url = "https://www.googleapis.com/youtube/v3/channels"

params = {
    "part": "id,snippet",
    "forHandle": "@ethioforum",
    "key": API_KEY,
}

response = requests.get(url, params=params)

print(response.status_code)

data = response.json()
print(data)
