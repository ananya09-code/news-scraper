from apify_client import ApifyClient

import os

APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not APIFY_TOKEN:
    raise RuntimeError("APIFY_TOKEN is not set")

client = ApifyClient(token=APIFY_TOKEN)

actor = client.actor("coregent/tiktok-video-scraper")

run_input = {
    "findVideosBy": [
        "https://www.tiktok.com/@nahom_fonti"
    ],
    "includeReposts": False,
    "maxVideos": 5,
    "scrapeRelatedVideos": False,
    "shouldDownloadAvatars": False,
    "shouldDownloadCovers": False,
    "shouldDownloadMusicCovers": False,
    "shouldDownloadSlideshowImages": False,
    "shouldDownloadVideos": False,
}

run = actor.call(run_input=run_input)

if run:
    dataset = client.dataset(run.default_dataset_id)
    items = dataset.list_items().items
    for item in items:
        print("Title:", item.get("caption"))
        print("URL:", item.get("videoUrl"))
        print("Date:", item.get("createTimeISO"))
        print("Views:", item.get("views"))
        print("Likes:", item.get("likes"))
        print("Comments:", item.get("comments"))
        print("Thumbnail:", item.get("videoCoverUrl"))
        print("-" * 50)
