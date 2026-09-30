import scrapy


class FanaSpider(scrapy.Spider):
    name = "fana"

    start_urls = [
        "https://www.fanamc.com/archives/category/localnews"
    ]

    def parse(self, response):

        for item in response.css("article.listing-item-blog"):

            yield response.follow(
                item.css("h2.title a::attr(href)").get(),
                callback=self.parse_article,
                meta={
                    "title": item.css("h2.title a::text").get(),
                    "author": item.css(
                        "div.post-meta a.post-author-a i.post-author.author::text"
                    ).get(),
                    "date": item.css(
                        "div.post-meta span.time time.post-published.updated::text"
                    ).get(),
                    "summary": item.css(
                        "div.post-summary::text"
                    ).get(),
                }
            )

    def parse_article(self, response):

        yield {
            "title": response.meta["title"].strip(),
            "author": response.meta["author"].strip(),
            "date": response.meta["date"].strip(),
            "summary": response.meta["summary"].strip(),
            "article": [
                paragraph.strip()
                for paragraph in response.css(
                    "div.entry-content.single-post-content p::text"
                ).getall()
            ]}
