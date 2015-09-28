#!/usr/bin/env python2

# Scrapes zenius-i-vanisher for DDR song data

import os
import sys
import argparse
import json
from collections import namedtuple

import requests
from bs4 import BeautifulSoup


def main():

    (mix, output_file) = parse_arguments()

    page_html = scrape_page(mix.number)
    (mix_table, songs_table) = get_mix_and_songs_tables(page_html)

    mix = get_mix_data(mix_table)
    mix['songs'] = get_song_data(songs_table)

    with open(os.path.abspath(output_file), 'w') as file:
        file.write(json.dumps(mix))


def parse_arguments():
    """Parse passed arguments & return a mix & output file"""

    # Store the mix 'key' and 'number'
    # 'key' is identifying mix name passed to this script
    # 'number' is the unique number identifying the mix on zenius
    Mix = namedtuple('Mix', ['name', 'number'])

    # Tuple of Mix namedtuples to iterate over & check
    mixes = (
        Mix('1st', 131),
        Mix('2nd', 134),
        Mix('3rd', 132),
        Mix('3rd_plus', 142),
        Mix('4th_plus', 145),
        Mix('5th', 146),
        Mix('6th_max', 147),
        Mix('7th_max2', 88),
        Mix('euromix2', 77),
        Mix('extreme', 81),
        Mix('supernova', 238),
        Mix('supernova2', 89),
        Mix('x', 148),
        Mix('x2', 286),
        Mix('x3', 347),
        Mix('2013', 1129),
    )

    parser = argparse.ArgumentParser()
    parser.add_argument('mix', nargs='?',
                        help='DDR mix to scrape')
    parser.add_argument('-o', dest='output',
                        help='Output file name')
    parser.add_argument('-l', dest='list', action='store_true',
                        help='List available mixes')

    args = parser.parse_args()

    # List the available mixes if requested
    if args.list:
        print 'Available Mixes:'
        print '\n'.join([x.name for x in mixes])
        sys.exit()

    # Make sure we were given a valid mix
    try:
        mix = [x for x in mixes if x.name == args.mix].pop()
    except IndexError:
        parser.print_help()
        sys.exit(1)

    if not args.output:
        args.output = mix.name + '.json'

    return (mix, args.output)


def scrape_page(mix_number):
    """Generates a URL & scrapes the page

    :param mix_number: The ID number for the desired mix
    """

    url = 'http://zenius-i-vanisher.com/v5.2/gamedb.php?gameid=%s&show_notecounts=1&sort=songname&sort_order=asc' % mix_number  #noqa
    print url

    r = requests.get(url)
    if r.status_code != 200:
        print 'Error retrieving page: %d' % r.status_code
        sys.exit(1)

    return r.text


def get_mix_and_songs_tables(page_html):
    """Pulls out tables containing mix & song data from html page data
    The table that starts with '<th>Data</th>' blah blah is the Mix data
    The table with the most children is the Songs data

    :param page_html: The scraped page's html
    """

    tables = BeautifulSoup(page_html, 'html.parser').findAll('table')

    longest = 0
    for i, table in enumerate(tables):
        th = table.findNext('th')
        if th and 'Data' in th.get_text():
            mix_table = table

        # Look for the longest table
        if tables[i] > tables[longest]:
            longest = i

    songs_table = tables[longest]

    return (mix_table, songs_table)


def get_mix_data(table):
    """Parse the mix table & return a dict with Mix data"""

    mix = {}

    for row in table.findAll('tr'):
        cols = row.findAll('td')
        if not cols:
            continue

        label = cols[0].get_text().lower()

        if 'name' in label:
            value = 'name'
        elif 'release date' in label:
            value = 'release'
        elif 'region' in label:
            value = 'region'
        else:
            continue

        mix[value] = cols[1].get_text()

    return mix


def get_song_data(table):
    """Parse the song table & return a list of song & chart information"""

    songs = []
    for row in table.findAll('tr'):
        # Placeholder dict for this song
        song = {
            'name': '',
            'name_translation': '',
            'artist': '',
            'artist_translation': '',
            'bpm': '',
            'genre': '',
            'unlock': '',
            'single': {
                'beginner': None,
                'basic': None,
                'difficult': None,
                'expert': None,
                'challenge': None,
            },
            'double': {
                'basic': None,
                'difficult': None,
                'expert': None,
                'challenge': None,
            },
        }

        # Pull out general song data (song name, artist, genre)
        song_data = row.find('td', attrs={'class': 'border'}).extract()

        # SONG NAME & TRANSLATION
        song_name_data = song_data.strong.extract()
        song['name'] = song_name_data.get_text().strip()
        try:
            song['name_translation'] = song_name_data.span['onmouseover'][16:-2]
        except TypeError:
            pass

        # SONG GENRE
        genre = song_data.find('span', attrs={'class': 'rightfloat'}).extract()
        song['genre'] = genre.get_text().strip()

        # SONG ARTIST & TRANSLATION
        song['artist'] = song_data.get_text().strip()
        try:
            song['artist_translation'] = song_data.span['onmouseover'][16:-2]
        except TypeError:
            pass

        # SONG BPM
        song['bpm'] = row.find('td', attrs={'class': 'border centre'}).get_text()  #noqa

        # UNLOCK DATA
        try:
            song['unlock'] = song_data.img['title']
        except TypeError:
            pass

        # SONG CHART DATA
        for col in row.findAll('td'):
            # Beginner is 'lightblue'
            if 'lightblue' in col.attrs.get('class', []):
                difficulty = 'beginner'
            # Basic is 'yellow'
            elif 'yellow' in col.attrs.get('class', []):
                difficulty = 'basic'
            # Difficult is 'fuchsia'
            elif 'fuchsia' in col.attrs.get('class', []):
                difficulty = 'difficult'
            # Expert is 'green'
            elif 'green' in col.attrs.get('class', []):
                difficulty = 'expert'
            # Challenge is 'purple'
            elif 'purple' in col.attrs.get('class', []):
                difficulty = 'challenge'
            else:
                continue

            # If we're here, this is a valid chart
            # Placeholder dict for this chart
            chart_dict = {
                'difficulty': None,
                'step': None,
                'freeze': None,
                'shock': None,
            }

            # This is a check to see if this is a singles or doubles chart
            # If it exists in song['single'], this chart must be double
            if not song['single'][difficulty]:
                style = 'single'
            else:
                style = 'double'

            chart_dict['difficulty'] = col.strong.extract().get_text().strip()

            # If this difficulty is '-', this chart doesn't exist
            if '-' in chart_dict['difficulty']:
                continue

            chart_data = col.small.get_text().strip().split(' / ')

            for value in ('step', 'freeze', 'shock'):
                try:
                    chart_dict[value] = chart_data.pop(0)
                except IndexError:
                    chart_dict[value] = ''

            song[style][difficulty] = chart_dict

        songs.append(song)
    return songs


if __name__ == '__main__':
    main()
