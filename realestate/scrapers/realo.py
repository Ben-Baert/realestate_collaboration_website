from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import re
import ast
from sortedcontainers import SortedSet
import datetime
from time import sleep
from functools import wraps
from selenium.webdriver.common.keys import Keys
import twiggy


class HouseSoldError(Exception):
    pass


class DriverBase:
    def __init__(self):
        self.driver = webdriver.PhantomJS()
        self.driver.implicitly_wait(10)
        self.driver.set_window_size(1280, 800)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.driver.close()
        self.driver.quit()


class RealoSearch(DriverBase):
    def __init__(self,
                 include_houses=True,
                 include_land=True,
                 min_price=50000,
                 max_price=200000,
                 min_landsize=300,
                 min_yearbuilt=1970,
                 max_age=7):
        super().__init__()
        self.log = twiggy.log.name("RealoSearch")
        min_date = (datetime.datetime.now() -
                    datetime.timedelta(days=max_age))
        min_date = min_date.strftime("%Y-%m-%d")
        search = []
        if include_houses:
            search.append("huis")
        if include_land:
            search.append("grond")
        search = ','.join(search)
        url = "https://www.realo.be/nl/search/{}/te-koop".format(search)
        url += "?priceMin={}".format(min_price)
        url += "&priceMax={}".format(max_price)
        url += "&landsizeMin={}".format(min_landsize)
        url += "&yearbuiltMin={}".format(min_yearbuilt)
        url += "&firstListing={}".format(min_date)
        self.url = url
        self.log.info("Scraping " + self.url + " for houses links.")
        self.driver.get(self.url)
        self.driver.find_element_by_css_selector("li.view-switch-item.list").click()

    def houses_urls(self):
        for link in self.driver.find_elements_by_css_selector(
            """
            li.component-estate-list-grid-item  > div > div:nth-child(2) > a.link
            """):
            self.log.debug("Found " + link.get_attribute("href"))
            yield link.get_attribute("href")
        try:
            self.next_page()
        except StopIteration:
            return
        else:
            print("going to the next one")
            yield from self.houses_urls()

    def next_page(self):
        try:
            self.driver.find_element_by_css_selector(
                """
                .button-next
                """).click()
            sleep(5)
        except NoSuchElementException:
            raise StopIteration


class Realo(DriverBase):
    def __init__(self, url):
        if "realo" not in url:
            log.error("A non-realo url was entered: {}".format(url))
            raise ValueError("Url must be a realo url")
        super().__init__()
        self.url = url
        self.log = twiggy.log.name("Realo").fields(url=url)
        self.driver.get(self.url)
        self.picture_count = self.number_of_pictures()

    def carousel_method(func):
        @wraps(func)
        def inner(self, *args, **kwargs):
            self.click_on_carousel()
            result = func(self, *args, **kwargs)
            self.click_on_carousel()
            return result
        return inner

    def click_on_carousel(self):
        elem = self.driver.find_element_by_css_selector(
            """
            #mediaViewer > ul.navigation.hidden-xs > li.active
            """)
        elem.click()
        sleep(2)

    def seller(self):
        try:
            return self.driver.find_element_by_css_selector(
                        """
                        a.font-medium:nth-child(1)
                        """).text
        except NoSuchElementException:
            return None

    def realestate_type(self):
        try:
            d = (self.driver
                 .find_element_by_css_selector(".property-type")
                 .text
                 .lower())
        except NoSuchElementException:
            return None
        if "grond" in d:
            return "land"
        return "house"

    def added_on(self):
        try:
            date_string = self.driver.find_element_by_css_selector(
                """
                .no-bottom-border
                > td:nth-child(1)
                > span:nth-child(1)
                """).text
        except:
            print("No added date on " + self.url)
            return None
        try:
            return datetime.datetime.strptime(date_string, "%d/%m/%y")
        except:
            return None

    def address(self):
        try:
            return (self
                    .driver
                    .find_element_by_css_selector(
                         """
                         #container
                         > div
                         > div:nth-child(1)
                         > div
                         > div.module.module-description
                         > header
                         > div
                         > h2
                         > span
                         """).text)
        except:
            self.log.debug("No address")

    def lat_lng(self):
        try:
            return tuple(float(x) for x in ast.literal_eval(
                            self
                            .driver
                            .find_element_by_css_selector(
                                """
                                #mediaViewer
                                """)
                            .get_attribute('data-latlng')))
        except:
            self.log.debug("No lat/lng information")

    def price(self):
        try:
            price = (self
                     .driver
                     .find_element_by_css_selector(
                        """
                        span.row:nth-child(1)
                        """)
                     .text[2:]
                     .replace(".", "")
                     .replace("+", ""))
            return int(price)
        except (ValueError, TypeError, NoSuchElementException):
            raise HouseSoldError(
                    """
                    It looks like the house at {} is no longer available.
                    Best to check manually though!
                    """.format(self.url))

    def area(self):
        inhabitable = None
        total = None
        for item in (self
                     .driver
                     .find_elements_by_css_selector(
                        """
                        .basic-details > div > div
                        """)):
            title = item.find_element_by_css_selector(".title")
            if title.text.lower() == "bewoonbaar":
                inhabitable = int(item
                                  .find_element_by_css_selector(".value")
                                  .text
                                  .replace("m2", "")
                                  .replace(".", ""))
            elif title.text.lower() == "grond":
                total = int(item
                            .find_element_by_css_selector(".value")
                            .text
                            .replace("m2", "")
                            .replace(".", ""))
            if inhabitable and total:
                break
        return inhabitable, total

    def information(self):
        try:
            for item in (self
                         .driver
                         .find_elements_by_css_selector(
                            """
                            #container
                            > div
                            > div.col.col-2-3.left.col-md-10.col-sm-12.push-md-1.col-xs-12
                            > div
                            > div.module.module-details
                            > ul
                            > li
                            """)):
                yield item.text.split("\n")
        except:
            self.log.debug("No information")

    def features(self):
        try:
            features = (self
                        .driver
                        .find_element_by_css_selector(
                            """
                            .tags
                            """))
        except NoSuchElementException:
            self.log.debug("No features")
            return []
        return (feature.text.title()
                for feature in features.find_elements_by_css_selector("li"))

    def description(self):
        try:
            return self.driver.find_element_by_css_selector(
                """
                .module-description
                > p:nth-child(4)
                """).text
        except NoSuchElementException:
            self.log.debug("No description found")
            return None

    @carousel_method
    def thumbnail_pictures(self):
        images = SortedSet()
        images_elements = self.driver.find_elements_by_css_selector(
            """
            div.pswp__carousel-item
            > a
            > img
            """)
        self.log.debug(str(len(images)) + " scraped from thumbnail pictures")
        for image in images_elements:
            url = image.get_attribute('src')
            print(url)
            images.add(url)
        return images

    def number_of_pictures(self):
        try:
            text = self.driver.find_element_by_css_selector(".numbers").text
            return int(re.search(r"(\d+)$", text).group(1))
        except:
            self.log.debug("No main pictures found")
            return 0

    @carousel_method
    def main_pictures(self):
        images = SortedSet()
        for _ in range(self.picture_count):
            for img in self.driver.find_elements_by_css_selector("img.pswp__img"):
                url = img.get_attribute("src")
                images.add(url)
            elem = self.driver.find_element_by_css_selector(".pswp__container")
            elem.send_keys(Keys.ARROW_RIGHT)
            sleep(0.5)
        self.log.debug(str(len(images)) + " scraped")
        return images
