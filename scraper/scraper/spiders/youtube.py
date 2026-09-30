import scrapy


class YoutubeSpider(scrapy.Spider):
    name = "youtube"

    start_urls = [
        "https://www.youtube.com/results?search_query=Math"
    ]

    def parse(self, response):
        for link in response.css("a"):
            href = link.css("::attr(href)").get()

            if href and "/watch?v=" in href:
                title = link.css("::attr(aria-label)").get()

                yield {
                    "title": title,
                    "url": response.urljoin(href),
                }
