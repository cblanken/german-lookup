# German Language to English Lookup

## Installation / Setup
Install the script requirements with `pip install -r requirements.txt`

### APIs
The following APIs are utilized. They are all either free or provide a free tier or
free usage up to a particular threshold.
- Linguatools
- dwds
- Google TTS

Depending on the chosen options, you will need to setup the API keys and corresponding
accounts for these APIs.

## Usage
```
# Translate german word and save anki file
python glwl.py -a noch

# Translate german word and save anki file with Google TTS sound file
python glwl.py -a -g noch
```

## Anki Output Format
By default the `--anki`/`-a` option will save the selected translation into a
semicolon-delimited text file that can be imported as an Anki card.

The format is like so:
```
german_word;part_of_speech;;[sound:sound_file_name];gender;english_translation;german_example_sentence;translated_example_sentence
```

Example
```
entdecken;verb;;[sound:entdeckt-de-DE-Wavenet-A.wav];;find/discover;Auf jedem Level gibt es allerlei Sammelgegenstände zu <b>entdecken</b> – durchsuche also jeden Winkel, um alles zu finden!;There are loads of collectibles to <b>find</b> in every stage, so search every corner to track everything down!
```

## Demo
TODO: add asciinema demo gif


