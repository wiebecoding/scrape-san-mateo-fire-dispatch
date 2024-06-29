import requests
from bs4 import BeautifulSoup as Soup
import httpx
import json
import datetime
import pytz
import argparse

url = "http://www.firedispatch.com/iPhoneActiveIncident.asp?Agency=04100"


def scrape_page(url):
    date = str(datetime.datetime.now(pytz.timezone("America/Los_Angeles")).date())
    html = httpx.get(url).text
    bits = [
        b.strip()
        for b in html.split("</TABLE>")[0].split("<TR><TD HEIGHT=4></TD></TR>")[1:]
    ]
    events = []
    for bit in bits:
        if not bit:
            continue
        tds = Soup(bit, "html.parser").select("td")
        if not tds or len(tds) < 4:
            continue
        time, id = tds[0].text.strip().replace("\xa0", " ").rsplit(None, 1)
        summary = tds[1].text.strip()
        category = tds[2].text.strip()
        location = tds[3].text.strip()
        latitude = None
        longitude = None
        # If there is a maps.google.com link get lat/lon
        map_link = tds[3].select("a[href^='https://maps.google.com']")
        if map_link:
            map_bits = map_link[0]["href"].split("q=")[1]
            try:
                latitude, longitude = map(float, map_bits.split(","))
            except ValueError:
                # Likely ValueError: could not convert string to float: ''
                pass
        units = tds[4].text.strip().replace("\xa0", " ")
        events.append(
            {
                "id": id,
                "date": date,
                "time": time,
                "summary": summary,
                "category": category,
                "location": location,
                "latitude": latitude,
                "longitude": longitude,
                "units": units,
            }
        )
    return html, events


def create_message(incident):
    info = "Incident Identified: " + incident["category"] + " at time " + incident["time"] + " with dept " + incident["summary"] + " at " + incident["location"] + ". Note: This is an address on the street, not necessarily at Nonnie and Pa's"
    return info


def ident_location(json, number, api_key, street):
    #print(send_message(create_message(json[0]), api_key, number))
    for incident in json:
        if incident["location"] == street:
            text_info = create_message(incident)
            send_message(text_info, api_key, number, street)


def send_message(info, apiKey, number, street):
    return requests.post(
        "https://api.mailgun.net/v3/alert.brianmwiebe.com/messages",
        auth=("api", apiKey),
        data={"from": "mailgun@alert.brianmwiebe.com",
              "to": number,
              "subject": "Alert for " + street,
              "text": info})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--street", help="Street Name", required=True)
    parser.add_argument("-n", "--number", help="Phone Number in email form", required=True)
    parser.add_argument("-a", "--apikey", help="API Key", required=True)
    args = parser.parse_args()
    html, events = scrape_page(url)
    ident_location(events, args.number, args.apikey, args.street)
