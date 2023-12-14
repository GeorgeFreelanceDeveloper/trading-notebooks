import logging
import logging.config
import os

import pandas as pd
import requests
from lxml import html



def download_images(trades: pd.DataFrame, output_directory: str) -> pd.DataFrame:
    response = []

    for index, trade in trades.iterrows():
        try:
            trade_id = __build_trade_id(trade["Asset"], trade["Date"], trade["Direction"])

            final_path = output_directory + trade_id

            if not os.path.exists(final_path):
                os.mkdir(final_path)

            __download_image_from_tw_url(trade["Context"], "{}/{}_context.png".format(final_path, trade_id))
            __download_image_from_tw_url(trade["Detail"], "{}/{}_detail.png".format(final_path,trade_id))
            __download_image_from_tw_url(trade["Detail2"], "{}/{}_detail2.png".format(final_path, trade_id))
            __download_image_from_tw_url(trade["Control"], "{}/{}_control.png".format(final_path, trade_id))

            response.append({"trade_id": trade_id, "status": "ok"})
        except:
            trade_id = __build_trade_id(trade["Asset"], trade["Date"], trade["Direction"])
            response.append({"trade_id": trade_id, "status": "not_ok"})
    
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


def __build_trade_id(asset: str, date: str, direction: str) -> str:
    date_array = date.split(".")
    day = date_array[0]
    month = date_array[1]
    year = date_array[2]

    if len(day) < 2:
        day = "0{}".format(day)

    if len(month) < 2:
        month = "0{}".format(month)

    return "{}{}{}_{}_{}".format(year, month, day, asset, direction)


def __parse_image_url_from_page(url: str) -> str:
    response = requests.get(url)

    if not response.ok:
        print(response)
        raise Exception("Problem with parse image url from page")

    html_page = html.fromstring(response.text)
    return html_page.xpath("//img")[0].attrib["src"]


    
    