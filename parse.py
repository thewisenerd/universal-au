# find 'Universal Pictures Australia' -name '*.info.json' > UniversalPicturesAU.txt
# python3.11 parse.py 'UniversalPicturesAU.txt' 'UniversalPicturesAU.csv'

import argparse
import csv
import dataclasses
import json
import os
import re
import typing

from whois import WhoisEntry
from whois.parser import PywhoisError

from whocache import whois

parser = argparse.ArgumentParser()
parser.add_argument('FILE')
parser.add_argument('OUTPUT')


@dataclasses.dataclass
class Result:
    id: str
    date: str
    title: str
    url: str


@dataclasses.dataclass
class ResultWhois:
    result: Result
    whois: typing.Union[WhoisEntry, PywhoisError]


regex = r"(www\.)?\w(?:[\w-]{0,61}\w)\.com(\.au)?"
banned = {
    'www.facebook.com',
    'facebook.com',
    'www.twitter.com',
    'twitter.com',
    'www.youtube.com',
    'www.instagram.com',
    'instagram.com',
    'www.tiktok.com',
    'www.universalpictures.com.au',
    'talenthouse.com',
}


def parse_data(data: dict) -> list[Result]:
    results: list[Result] = []

    if 'upload_date' not in data:
        return results

    yt_id: str = data['id']
    desc: str = data['description']
    title: str = data['title']
    date: str = data['upload_date']

    matches = re.finditer(regex, desc, re.MULTILINE)
    for match in matches:
        url = match.group()
        if url.lower() not in banned:
            results.append(Result(yt_id, date, title, url))

    return results


def check_files(file_list: list[str], output: str):
    results: list[Result] = []
    final: list[ResultWhois] = []

    for file in file_list:
        with open(file) as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"failed to parse json {file=}", e)
                raise e
        data_result: list[Result]
        try:
            data_result = parse_data(data)
        except Exception as e:
            print(f"failed to parse data {file=}", e)
            raise e
        for r in data_result:
            results.append(r)

    url_first: dict[str, str] = {}
    for r in results:
        new = r.date
        if r.url in url_first:
            old = url_first[r.url]
            if new < old:
                url_first[r.url] = new
        else:
            url_first[r.url] = new

    results.sort(key=lambda x: url_first[x.url])

    r: Result
    for (idx, r) in enumerate(results):
        print(f"[{idx}/{len(results)}] {r.date} / {r.url}")
        w = whois(r.url, file_name='whois.cache')
        final.append(ResultWhois(r, w))

    rw: ResultWhois
    with open(output, 'w') as w:
        writer = csv.writer(w)
        rh = ['date', 'title', 'yt_id', 'url']
        dh = ['active', 'registrant', 'debug']

        writer.writerow(rh + dh)
        for rw in final:
            r: Result = rw.result
            p = rw.whois

            debug: str = ''
            active: bool
            registrant: typing.Optional[str]
            if type(p) == PywhoisError:
                active = False
                registrant = None

                debug = str(p)
                if 'No match for' in debug:
                    active = False  # is active = unknown until this?
            else:
                domain = p['domain_name']
                active = domain is not None
                registrant = p['registrant_name'] if 'registrant_name' in p else None

                # if registrant is None:
                #     debug = str(p)

            ro = [r.date, r.title, r.id, r.url]
            do = [active, registrant, debug]

            writer.writerow(ro + do)


def main():
    args = parser.parse_args()
    inp = args.FILE
    inp_abs = os.path.abspath(inp)
    if not os.path.isfile(inp_abs):
        raise Exception(f"file does not exist FILE={inp}")

    lines: list[str]
    with open(inp_abs) as f:
        lines = [x.strip() for x in f.read().splitlines()]

    check_files(lines, args.OUTPUT)


if __name__ == '__main__':
    main()
