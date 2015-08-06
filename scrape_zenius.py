#!/usr/bin/env python2

# Scrapes zenius-i-vanisher for DDR song data
# Outputs the data to a json file that can be imported with:
#     import_json_song_data.py

import os
import sys
import argparse
import json

import requests
from bs4 import BeautifulSoup


def parse_arguments():
    # Game ID mapping with ZiV
    gameids = {
        "1st": 131,
        "2nd": 134,
        "3rd": 132,
        "3rd_plus": 142,
        #  "4th": 0,  # Zenius is missing data for this
        "4th_plus": 145,
        "5th": 146,
        "6th_max": 147,
        "7th_max2": 88,
        "euromix2": 77,
        "extreme": 81,
        "supernova": 238,
        "supernova2": 89,
        "x": 148,
        "x2": 286,
        "x3": 347,
        "2013": 1129,
    }

    parser = argparse.ArgumentParser()
    parser.add_argument("mix", nargs="?", help="Mix you'd like to scrape")
    parser.add_argument("-l", "--list", action="store_true",
                        help="List available mixes")

    args = parser.parse_args()

    # If a mix isn't provided, we can't proceed
    if args.mix and args.mix in gameids.keys():
        args.mix = gameids[args.mix]
        return args
    else:
        print "Available Mixes:"
        print ",".join(sorted(gameids.keys()))
        sys.exit(1)


def get_mix_data(tables):
    mix = {}

    # The mix information is in the 1st table on the page
    for row in tables[0].findAll("tr"):
        cols = row.findAll("td")
        if cols:
            label = cols[0].getText().lower()

            if "name" in label:
                mix["name"] = cols[1].getText()

                # ZiV gave 2013/2014 a dumb name
                if mix["name"] == "DanceDanceRevolution (New)":
                    mix["name"] = "DanceDanceRevolution 2013"
            elif "release date" in label:
                mix["release"] = cols[1].getText()
            elif "region" in label:
                mix["region"] = cols[1].getText()
    return mix


def get_song_data(tables, mix):
    # A few mixes store the song info in a different table
    if mix["name"] == "Dance Dance Revolution 3rdMIX PLUS" or\
            mix["name"] == "Dance Dance Revolution 4thMIX PLUS" or\
            mix["name"] == "Dancing Stage EuroMIX2":
        table_num = 1
    else:
        table_num = 2

    songs = []
    for row in tables[table_num].findAll("tr"):
        song = {
            "name": "",
            "name_translation": "",
            "artist": "",
            "artist_translation": "",
            "bpm": "",
            "genre": "",
            "single": {
                "beginner",
                "basic",
                "difficult",
                "expert",
                "challenge",
            },
            "double": {
                "basic",
                "difficult",
                "expert",
                "challenge",
            },
        }

        song_data = row.find("td", attrs={"class": "border"})

        # Song's genre
        genre = song_data.find("span", attrs={"class": "rightfloat"}).extract()
        song["genre"] = genre.get_text().strip()

        # Song Name & translation if applicable
        try:
            song["name_translation"] =\
                song_data.strong.span["onmouseover"][16:-2]
        except TypeError:
            pass
        song["name"] = song_data.strong.extract().get_text().strip()

        # Artist & translation if applicable
        try:
            song["artist_translation"] = song_data.span["onmouseover"][16:-2]
        except TypeError:
            pass
        song["artist"] = song_data.get_text().strip()

        # Song's bpm
        song["bpm"] = row.find(
            "td",
            attrs={"class": "border centre"}
        ).get_text()

        # Gather chart data
        (song["single"], song["double"]) = get_chart_data(row)

        songs.append(song)

    return songs


def get_chart_data(row):
    difficulties = {
        "lightblue": "beginner",
        "yellow": "basic",
        "fuchsia": "difficult",
        "green": "expert",
        "purple": "challenge"
    }

    single = {}
    double = {}

    for difficulty in difficulties:
        chart_list = row.findAll("td", attrs={"class": "centre " + difficulty})

        # Older mixes won't have beginner or challenge steps
        if not chart_list:
            continue

        # Iterate over singles & doubles charts for current difficulty
        for count in range(2):
            # Doubles doesn't have beginner steps
            try:
                style = chart_list[count]
            except IndexError:
                continue

            # Some songs don't have charts of certain difficulties
            # Example: challenge only songs
            if not style.small:
                continue

            steps_freeze = style.small.extract().get_text().strip().split(" / ")

            stats = {}
            stats["step_count"] = steps_freeze[0]

            # Some songs don't have freezes or shock arrows
            if len(steps_freeze) == 2:
                stats["freeze_count"] = steps_freeze[1]
                stats["shock_count"] = 0
            elif len(steps_freeze) == 3:
                stats["freeze_count"] = steps_freeze[1]
                stats["shock_count"] = steps_freeze[2]
            else:
                stats["freeze_count"] = 0
                stats["shock_count"] = 0

            stats["difficulty"] = style.get_text().strip()

            # Convert all strings to integers
            for attr in stats.keys():
                try:
                    stats[attr] = int(stats[attr])
                except ValueError:
                    stats[attr] = 0

            # Single or Double
            if count:
                double[difficulties[difficulty]] = stats
            else:
                single[difficulties[difficulty]] = stats

    return (single, double)


def main():
    # Set the path to our data dir
    data_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__))[:-4],
        "data"
    )

    args = parse_arguments()
    url = "%s%s%s" % (
        "http://zenius-i-vanisher.com/v5.2/gamedb.php?gameid=",
        str(args.mix),
        "&show_notecounts=1&sort=songname&sort_order=asc",
    )

    # Grab our page
    r = requests.get(url)
    if r.status_code != 200:
        print "Error retrieving page: %d" % r.status_code
        sys.exit(1)
    soup_data = BeautifulSoup(r.text)
    tables = soup_data.findAll("table")

    # Parse our mix data
    mix = get_mix_data(tables)

    # Add songs to our mix
    mix["songs"] = get_song_data(tables, mix)

    filename = os.path.join(data_dir, mix["name"] + ".json")
    with open(filename, "w+") as output_file:
        output_file.write(json.dumps(mix))


if __name__ == "__main__":
    main()
