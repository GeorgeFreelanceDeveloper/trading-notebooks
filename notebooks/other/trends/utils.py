import logging
import logging.config
import os

import pandas as pd
import requests
from lxml import html

def transform_data(trends_raw: pd.DataFrame) -> pd.DataFrame:
    trends = trends_raw.copy()

    trends.insert(loc = 0, column = 'id', value = trends["ticker"] + "_" + trends["long_term_trend_year"].map(str))

    return trends

def download_images(trends: pd.DataFrame, output_directory: str) -> pd.DataFrame:
    response = []

    for index, trend in trends.iterrows():
        try:
            id = trend["id"]

            final_path = "{}/{}".format(output_directory, id)

            if not os.path.exists(final_path):
                os.mkdir(final_path)

            __download_image_from_tw_url(trend["long_term_trend_context"], "{}/{}_long_term_trend_context.png".format(final_path, id))
            __download_image_from_tw_url(trend["long_term_trend_detail"], "{}/{}_long_term_trend_detail.png".format(final_path, id))
            __download_image_from_tw_url(trend["medium_term_trend_context"], "{}/{}_medium_term_trend_context.png".format(final_path, id))
            __download_image_from_tw_url(trend["medium_term_trend_detail"], "{}/{}_medium_term_trend_detail.png".format(final_path, id))

            response.append({"trend_id": trend["id"], "status": "ok"})
        except:
            response.append({"trend_id": trend["id"], "status": "not_ok"})


    return pd.DataFrame(response)



# ---------------------------------
# Private method
# ---------------------------------
def __download_image_from_tw_url(url: str, file_path: str) -> None:
    if pd.isna(url):
        print("Invalid url [{}], image will not be download.".format(url))
        return

    with open(file_path, 'wb') as handle:
        pic_url = __parse_image_url_from_page(url)
        response = requests.get(pic_url, stream=True)

        if not response.ok:
            logging.info(response)

        for block in response.iter_content(1024):
            if not block:
                break

            handle.write(block)

def __parse_image_url_from_page(url: str) -> str:
    response = requests.get(url)

    if not response.ok:
        print(response)
        raise Exception("Problem with parse image url from page")

    html_page = html.fromstring(response.text)
    return html_page.xpath("//img")[0].attrib["src"]