import scrapy


class QuotesSpider(scrapy.Spider):
    name = "quotes"

    start_urls = [
        "https://jiji.com.et/search?query=iphone"
    ]

    def parse(self, response):
        for item in response.css("..."):
            yield {
                "title": item.css("...").get()
            }
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
