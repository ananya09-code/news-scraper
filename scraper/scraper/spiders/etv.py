import scrapy


class EtvSpider(scrapy.Spider):
    name = "etv"

    page = 1
    catid = 1

    start_urls = [
        f"https://www.ebc.et/Home/CategorialNews?CatId={catid}&page={page}"
    ]

    def parse(self, response):
        for item in response.css("article.news-card"):

            title = item.css(
                "div.news-content h2.news-title a::text"
            ).get()

            date = item.css(
                "div.news-content div.news-meta span.news-date span.timeago::text"
            ).get()

            url = item.css(
                "div.news-content h2.news-title a::attr(href)"
            ).get()

            if url:
                yield response.follow(
                    url,
                    callback=self.parse_article,
                    meta={
                        "title": title,
                        "date": date,
                    }
                )

    def parse_article(self, response):
        yield {
            "title": " ".join(response.meta["title"].split()),
            "date": " ".join(response.meta["date"].split()),
            "url": response.url,

            "article": " ".join(
                text.strip()
                for text in response.css(
                    "div.post-content.mb-4 ::text"
                ).getall()
                if text.strip()
            ), }
