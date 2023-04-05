#!/usr/bin/python

import os
import sys
import pathlib
from string import Template
import argparse
import requests
from pprint import pprint
from google.cloud import translate_v2 as translate

# TODO: test out DWDS API - https://www.dwds.de/d/api

parser = argparse.ArgumentParser(
        prog="glwl",
        description="German language lookup script",
        epilog="")

parser.add_argument('text', help="Word to lookup")
parser.add_argument('file', help="File to append lookup")
parser.add_argument('-a', '--anki', action='store_true', help="Output translation in Anki importable format")
parser.add_argument('-r', '--reverse', action='store_true', help="Do reverse lookup (English to German)")
parser.add_argument('-p', '--phrase', action='store_true', help="Phrase translation")

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

def translate_word_lingua(text: str, langpair: str, top_n: int):
    api_key = os.environ.get("GLWL_API_KEY")
    if api_key is None:
        print("Please provide an api key with the environment variable GLWL_API_KEY")
        sys.exit(0)

    headers = {
        "X-RapidAPI-Key": f"{api_key}",
        "X-RapidAPI-Host": "petapro-translate-v1.p.rapidapi.com",
    }

    # The API supposedly acceps a `min_freq` parameter to limit results to only
    # include translation that appear in the dataset more than `min_freq` times
    # but it didn't work when I tried it. So, filtering has to be done manually.
    URL = "https://petapro-translate-v1.p.rapidapi.com/"
    min_freq = 1
    querystring = {
        "langpair": langpair,
        "query": text,
    }
    resp = requests.get(URL, headers=headers, params=querystring);
    print(f"Endpoint: {resp.url}")

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
    english_word_translations = [x["l2_text"] for x in data]
    parts_of_speech = set([x["wortart"] for x in data])
    english_synonyms = [x["synonyme1"] for x in data]
    german_synonyms = [x["synonyme2"] for x in data]

    opts = []
    template = Template("$german;$pos;$pronunciation;$gender;$english;$example;$example_translated")
    
    if len(data) < 1:
        print("No translations found")
        sys.exit(0)
                
    for i, d in enumerate(data):
        if args.anki:
            try:
                params = {
                    "german": d['l2_text'],
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
                print(f"{i} → {line}")

        else:
            pprint(f"{i} → {data[i]}")
            opts.append(data[i])

    # Select option
    sel = -1
    while sel < 0 or sel > len(opts):
        try:
            sel = int(input(f"\nSelect one of the above 0-{len(opts)-1}: "))
        except ValueError:
            print("Invalid selection. Please enter a number in the provided range.");
            continue

    with open(pathlib.Path(args.file), "a", encoding="utf-8") as fp:
        fp.write(f"{opts[sel]}\n")

