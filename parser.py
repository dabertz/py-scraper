from lxml import html
import requests
import urllib.parse as urlparse
from time import sleep
from elasticsearch import Elasticsearch

es = Elasticsearch([{'host': 'localhost', 'port': '9200'}])

class AmazonScraper:

    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:64.0) Gecko/20100101 Firefox/64.0'
    ]

    BASE_URL = 'https://www.amazon.co.jp'

    products = []
    current_agent = 0
    MAX_TRIAL_REQUEST = 3

    def __init__(self, url):

        if es.ping():
            self.parse_search_result(url)
            # self.parse_product_page("B07HCH6GHQ", None)
        else:
            print("Elasticsearch is not connected")
        

    def parse_search_result(self, url):

        current_page_number = self.get_page_number(url)
        if current_page_number is None:
            current_page_number = 1

        trials = 0
        while trials < self.MAX_TRIAL_REQUEST:
            try:

                trials += 1
                response = requests.get(self.BASE_URL + url, headers=self._get_headers())
                doc = html.fromstring(response.content)
                xresult_items = doc.xpath("//div[contains(@class,'s-result-list')]//div[contains(@class,'s-result-item')]")
                if len(xresult_items) == 0:
                    raise Exception('No Result Found! Try again')

                for item in xresult_items:
                    asin = item.get('data-asin')
                    images = item.xpath('.//img[@class="s-image"]')
                    if (len(images) ==0):
                        print("[NO IMAGE] Skip ", asin)
                        continue
                    self.parse_product_page(asin, images[0].get('src'))

                xpagination = doc.xpath("//ul[@class='a-pagination']//li[@class='a-normal']//a")
                pages = {}
                for item in xpagination:
                    link = item.get("href")
                    page_number = self.get_page_number(link)
                    if page_number is not None and page_number > 0:
                        pages[page_number] = link

                next_page = current_page_number + 1
                if next_page in pages:
                    self.parse_search_result(pages[next_page])
                else:
                    print(len(self.products))

                break
            except Exception as e:
                print("ERROR:", e)

    def parse_product_page(self, asin, image_url):
        if asin in self.products:
            return

        product_url = self.BASE_URL + '/dp/' + asin

        # Try up to 3 trials
        trials = 0
        while trials < self.MAX_TRIAL_REQUEST:
            trials += 1
            try:
                response = requests.get(product_url, headers=self._get_headers())
                if response.status_code != 200:
                    raise Exception("Request Failed")
        
                doc = html.fromstring(response.content)

                xptitle = doc.xpath('//h1[@id="title"]//text()')
                xpsale_price = doc.xpath('//tr[@id="priceblock_ourprice_row"]//span[contains(@id, "priceblock_ourprice") or contains(@id,"saleprice")]//text()')
                xcategory = doc.xpath('//a[@class="a-link-normal a-color-tertiary"]//text()')
                xpreview = doc.xpath('//div[@id="averageCustomerReviews"]//i[contains(@class,"a-icon-star")]')

                if len(xptitle) <= 0:
                    raise Exception("Unable to find title. Try again.", asin)
                title = ''
                for txt in xptitle:
                    title += " ".join(txt.split())

                price_range = ''
                for txt in xpsale_price:
                    price_range += " ".join(txt.split())

                categories = []
                for txt in xcategory:
                    cat = " ".join(txt.split())
                    categories.append(cat)

                review_rate = None
                for item in xpreview:
                    cls = item.get('class').split()
                    for x in cls:
                        if x.startswith('a-star-'):
                            review_rate = x[7:].replace('-','.')
                            break

                data = {
                    'title': title,
                    'product_url': product_url,
                    'categories': categories,
                    'review_rate': review_rate,
                    'price': price_range ,
                    'image_url' : image_url
                }

                self._save_product(asin, data)
                self.products.append(asin)
                break
            except Exception as e:
                print(e)

            # Try after 2 second
            sleep(2)

    def _get_headers(self):
        self.current_agent = 1 if self.current_agent == 0 else 1
        headers = {
            'User-Agent': self.USER_AGENTS[self.current_agent],
            'Accept': 'text/html,application/xhtml+xml,\
                        application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        }
        return headers

    def get_page_number(self, url):
        query_string = urlparse.urlparse(url).query
        queries = urlparse.parse_qs(query_string)
        if 'page' in queries:
            return int(queries['page'][0])
        else:
            return None

    def _save_product(self, asin, data):
        es.index(index='amazon',doc_type='products',id=asin,body=data)
        print(asin)


if __name__ == "__main__":
    search_url = "/s?k=nike"
    scraper = AmazonScraper(search_url)