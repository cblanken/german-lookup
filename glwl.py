#!/usr/bin/python

import os
import sys
import pathlib
from string import Template
import argparse
import requests
from termcolor import colored, cprint
from pprint import pprint
#from google.cloud import translate_v2 as translate

# TODO: test out DWDS API - https://www.dwds.de/d/api
# TODO: Add Google TTS (Text-to-Speech) API integration

parser = argparse.ArgumentParser(
        prog="glwl",
        description="German language lookup script",
        epilog="")

parser.add_argument('text', help="Word to lookup")
parser.add_argument('file', nargs='?', default="anki_cards.txt", help="File to append lookup")
parser.add_argument('-a', '--anki', action='store_true', help="output translation in Anki importable format")
parser.add_argument('-r', '--reverse', action='store_true', help="do reverse lookup (English to German)")
parser.add_argument('-p', '--phrase', action='store_true', help="enable phrase translation")

args = parser.parse_args()

def translate_text_gcloud(source: str, target: str, text: str):
    client = translate.Client()

    result = client.translate(text, target_language=target, source_language=source)

    #result = translate_text("de", "en", args.text)
    #print(f"Deutsch → {args.text}")
    #print(f"English → {result['translatedText']}")
    
    return result

WORD_CLASSES = {
    "ADJ": "adj",
    "ADV": "adverb",
    "NOMEN": "noun",
    "PREP": "preposition",
    "VERB": "verb",
}

COLORS = ["light_yellow", "light_green", "light_blue", "light_magenta", "light_cyan"]

def translate_word_lingua(text: str, langpair: str, top_n: int):
    api_key = os.environ.get("GLWL_API_KEY")
    if api_key is None:
        print("Please provide an api key with the environment variable GLWL_API_KEY")
        sys.exit(0)

    headers = {
        "X-RapidAPI-Key": f"{api_key}",
        "X-RapidAPI-Host": "petapro-translate-v1.p.rapidapi.com",
    }

    # The API supposedly accepts a `min_freq` parameter to limit results to only
    # include translations that appear in the dataset more than `min_freq` times
    # but it didn't work when I tried it. So, filtering has to be done manually.
    URL = "https://petapro-translate-v1.p.rapidapi.com/"
    min_freq = 1
    querystring = {
        "langpair": langpair,
        "query": text,
    }
    resp = requests.get(URL, headers=headers, params=querystring);

    data = resp.json()

    # Filter results to only include translations that occured at least `min_freq`
    # times in the APIs corpus
    data = [x for x in data if x['freq'] > min_freq]

    # Sort by usage frequency
    data = sorted(data, key=lambda x: x['freq'], reverse=True)

    # Pick top_n most common usages
    data = data[:top_n]

    return data


if __name__ == "__main__":
    data = translate_word_lingua(args.text, "de-en", 5)
    opts = []
    template = Template("$german;$pos;$pronunciation;$gender;$english;$example;$example_translated")
    
    if len(data) < 1:
        print("No translations found")
        sys.exit(0)
                
    for i, d in enumerate(data):
        if args.anki:
            try:
                params = {
                    "german": d['l1_text'],
                    "pos": WORD_CLASSES[d['wortart']],
                    "pronunciation": "",
                    "gender": "",
                    "english": d['l2_text'],
                    "example": d['sentences'][0][0],
                    "example_translated": d['sentences'][0][1],
                }
                line = template.substitute(params)
            except IndexError as e:
                line = f"{d['l2_text']} - NO EXAMPLE SENTENCES AVAILABLE"
            finally:
                opts.append(line)
                print(f"{i} → ", end="")
                cprint(f"{line}", COLORS[i % len(COLORS)])

        else:
            pprint(f"{i} → {data[i]}")
            opts.append(data[i])

    # Select option
    sel = -1

    while sel < 0 or sel > len(opts):
        try:
            if len(opts) == 1:
                sel = int(input(f"\nSelect one of the above (0): "))
            else:
                sel = int(input(f"\nSelect one of the above (0-{len(opts)-1}): "))
        except ValueError:
            print("Invalid selection. Please enter a number in the provided range.");
            continue
        except KeyboardInterrupt:
            exit(0)

    with open(pathlib.Path(args.file), "a", encoding="utf-8") as fp:
        fp.write(f"{opts[sel]}\n")

