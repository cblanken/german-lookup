#!/usr/bin/python

import os
import sys
import pathlib
from string import Template
import argparse
import requests
from termcolor import colored, cprint
from pprint import pprint
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech as tts

# TODO: test out DWDS API - https://www.dwds.de/d/api
# TODO: implement English lookup
# TODO; Add selection for example sentences

parser = argparse.ArgumentParser(
        prog="glwl",
        description="German language lookup script",
        epilog="")

parser.add_argument('text', help="Word to lookup")
parser.add_argument('file', nargs='?', default="anki_cards.txt", help="File to append lookup")
parser.add_argument('-a', '--anki', action='store_true', help="output translation in Anki importable format")
parser.add_argument('-p', '--phrase', action='store_true', help="enable phrase translation")
parser.add_argument('-g', '--google-voices', action='store_true', help="enable gcloud text-to-speech")

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
    "KONJ": "conjuction",
    "NOMEN": "noun",
    "PREP": "preposition",
    "PRON": "pronoun",
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
    
    if resp.status_code != requests.codes.ok:
        return None

    data = resp.json()

    # Filter results to only include translations that occured at least `min_freq`
    # times in the APIs corpus
    data = [x for x in data if x['freq'] > min_freq]

    # Sort by usage frequency
    data = sorted(data, key=lambda x: x['freq'], reverse=True)

    # Pick top_n most common usages
    data = data[:top_n]

    return data

def get_voices(language_code: str = None, filter_text: str = ""):
    client = tts.TextToSpeechClient()
    response = client.list_voices(language_code=language_code)
    voices = sorted(response.voices, key=lambda voice: voice.name)
    voices = [x for x in voices if filter_text in x.name]
    return voices

def text_to_wav(voice: str, text: str):
    language_code = "-".join(voice.split("-")[:2])
    text_input = tts.SynthesisInput(text=text)
    voice_params = tts.VoiceSelectionParams(
        language_code=language_code,
        name=voice
    )
    audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16)

    client = tts.TextToSpeechClient()
    response = client.synthesize_speech(
        input=text_input,
        voice=voice_params,
        audio_config=audio_config,
    )

    return response
    

def save_sound_file(data, filename):
    target_dir = pathlib.Path("./sound")
    target_dir.mkdir(parents=True, exist_ok=True)
    with open(target_dir.joinpath(filename), "wb") as fp:
        fp.write(data)

if __name__ == "__main__":
    # Query linguatools for text translation
    data = translate_word_lingua(args.text, "de-en", 5)
    opts = []
    
    if data is None or len(data) == 0:
        print(f"No translations found for \"{args.text}\"")
        sys.exit(0)

    # Output translation options
    text = args.text
    if args.anki:

        for i, d in enumerate(data):
            try:
                line = "\n    ".join([
                    f"German: {d['l1_text']}",
                    f"English: {d['l2_text']}",
                    f"German Sentence: {d['sentences'][0][0]}",
                    f"English Sentence: {d['sentences'][0][1]}",
                ])
            except IndexError as e:
                line = f"{d['l2_text']} - NO EXAMPLE SENTENCES AVAILABLE"
            finally:
                opts.append(line)
                print(f"{i} → ", end="")
                cprint(f"{line}", COLORS[i % len(COLORS)])

        # Prompt user for translation selection
        data_sel = -1
        while data_sel < 0 or data_sel > len(opts):
            try:
                if len(opts) == 1:
                    data_sel = int(input(f"\nSelect one of the above (0): "))
                else:
                    data_sel = int(input(f"\nSelect one of the above (0-{len(opts)-1}): "))
            except ValueError:
                print("Invalid data_selection. Please enter a number in the provided range.");
                continue
            except KeyboardInterrupt:
                sys.exit(0)

        # Correct text if different from original query
        text = data[data_sel]['l1_text']
    else:
        opts = [f"{i} → {data[i]}" for i in range(0, len(data))]
        text = args.text


    # Query gcloud TTS for speech synthesis options
    sound_filename = ""
    if args.google_voices:
        print("Getting Google Wavenet voices...")
        voices = get_voices("de", "Wavenet")
        print(f" Voices: {len(voices)} ".center(60, "-"))
        for i, voice in enumerate(voices):
            languages = ", ".join(voice.language_codes)
            name = voice.name
            gender = tts.SsmlVoiceGender(voice.ssml_gender).name
            rate = voice.natural_sample_rate_hertz
            print(f"{i:<3}→ {languages:<8} | {name:<24} | {gender:<8} | {rate:,} Hz")

        wav_sel = -1
        if len(voices) == 1:
            wav_sel = 0
        else:
            try:
                wav_sel = int(input(f"\nSelect one of the voices (0-{len(voices)-1}): "))
            except KeyboardInterrupt:
                sys.exit(0)

        print(voices[wav_sel].name)

        # Get and save audio file of synthesized word
        wav_data = text_to_wav(voices[wav_sel].name, text)
        sound_filename = f"{args.text.replace(' ', '_')}-{voices[wav_sel].name}.wav"
        save_sound_file(wav_data.audio_content, sound_filename)

    # Query dwds data for pronunciation
    dwds = requests.get(f"https://www.dwds.de/api/ipa/?q={text[:20]}")
    dwds.encoding = 'utf-8'
    dwds_ipa = dwds.json() if dwds.status_code is requests.codes.ok else ""
    pronunciation = dwds_ipa[0]['ipa'] if len(dwds_ipa) > 0 else ""

    # Build template string for anki output
    if args.anki:
        template = Template("$german;$pos;$pronunciation;$sound_file;$gender;$english;$example;$example_translated\n")
        try:
            print("pronun", pronunciation)
            params = {
                "german": data[data_sel]['l1_text'],
                "pos": WORD_CLASSES[data[data_sel]['wortart']],
                "pronunciation": pronunciation,
                "sound_file": f"[sound:{sound_filename}]" if len(sound_filename) > 0 else "",
                "gender": "",
                "english": data[data_sel]['l2_text'],
                "example": data[data_sel]['sentences'][0][0],
                "example_translated": data[data_sel]['sentences'][0][1],
            }
            line = template.substitute(params)
        except IndexError as e:
            line = f"{data[data_sel]['l2_text']} - NO EXAMPLE SENTENCES AVAILABLE"
        finally:
            opts.append(line)
            cprint(f"{line}", COLORS[i % len(COLORS)])

        # Write data to text file for Anki import
        with open(pathlib.Path(args.file), "a", encoding="utf-8") as fp:
            fp.write(line)

