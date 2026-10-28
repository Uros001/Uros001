# Pronunciation Guide

Narration engine: Kokoro-82M (`af_heart`, American English) via kokoro-onnx. Corrections are applied as IPA overrides in `tools/tts_narration.py` (`PHONEME_FIX`) and verified by transcribing every sentence with Whisper small.en (`tools/asr_check.py`). "Verified" below means the speech recognizer heard the intended word, or a phonetically equivalent spelling of it.

| Term | Say it | IPA used | Note | Verified |
|---|---|---|---|---|
| pemmican | PEM-ih-kun | pˈɛmɪkən | espeak default is correct | ✅ |
| pimîhkân (Cree) | pih-MEE-kahn | pɪmˈiːhkɑːn | Cree source word, built on *pimiy*, "fat, grease". A Cree speaker's recording would be preferable for a future revision. | ✅ ("pimekon") |
| Métis | may-TEE | meɪtˈiː | espeak default "MAY-deez" was **wrong**, so overridden | ✅ ("may tea") |
| Assiniboia | uh-SIN-ih-BOY-uh | ɐsˈɪnɪbˌɔɪə | default is correct | ✅ |
| Assiniboine | uh-SIN-ih-boyn | ɐsˈɪnɪbˌɔɪn | default is correct | ✅ |
| Cree | KREE | kɹˈiː | | ✅ |
| Ojibwe | oh-JIB-way | oʊdʒˈɪbweɪ | default "ah-JIB-wee" overridden | ✅ |
| Miles Macdonell | mək-DON-əl | məkdˈɑːnəl | default "mək-DOH-nəl" overridden; the recognizer spells it "McDonald" (closest common word) | ✅ |
| Selkirk | SEL-kurk | sˈɛlkɚk | an earlier ɝ variant was heard as "Selk"; fixed | ✅ |
| Robert Semple | SEM-pəl | sˈɛmpəl | | ✅ |
| Cuthbert Grant | KUTH-bert | kˈʌθbɚt | | ✅ |
| Souris (River) | SOOR-iss | sˈʊɹɪs | the regional English pronunciation; default "SOW-er-iss" overridden | ✅ |
| Qu'Appelle | kuh-PELL | kəpˈɛl | default "kwa-PELL" overridden | ✅ |
| la Grenouillère | lah gren-oo-YAIR | lɑː ɡɹɛnuːjˈɛɹ | anglicized French; Frog Plain | ✅ (approximate) |
| la Victoire de la Grenouillère | lah veek-TWAR duh lah gren-oo-YAIR | lɑː viktwˈɑːɹ də lɑː ɡɹɛnuːjˈɛɹ | | ✅ (approximate) |
| Pierre Falcon | pyair FAL-kun | pjˈɛɹ fˈælkən | Métis songwriter | ✅ |
| Athabasca | ath-uh-BASK-uh | æθəbˈæskə | default stress was on the first syllable | ✅ |
| Fort Gibraltar | jih-BRAWL-ter | dʒɪbɹˈɔltɚ | | ✅ |
| Montreal | mon-tree-AWL | mˌɑːntɹɪˈɔːl | American pronunciation | ✅ |
| Roald Amundsen | ROH-ahl AH-mun-sen | ˈɑːmənsən | default "AM-und-sen" overridden | ✅ |
| William Hornaday | HOR-nuh-day | hˈɔːɹnɐdˌeɪ | | ✅ |
| Siksika | sik-SIK-uh | sɪksˈɪkə | Blackfoot Confederacy nation | ✅ ("Sixsika") |
| Piikani | pee-KAH-nee | piːkˈɑːni | Blackfoot Confederacy nation | ✅ ("Pekani") |
| saskatoons | sas-kuh-TOONZ | default | the berry | ✅ |

## Numbers and dates (text normalization)
espeak reads "1814" as "one thousand eight hundred fourteen", so years are converted to spoken form before synthesis: 1811 → "eighteen eleven", 1814 → "eighteen fourteen", 1870s → "eighteen seventies", 1889 → "eighteen eighty-nine", 1911 → "nineteen eleven", 2014 → "twenty fourteen". Other quantities are written out in words in the narration text itself ("four hundred and seventy-nine", "one thousand and ninety-one").

## Delivery notes
- Speed 0.82 (Kokoro scale), about 160–170 wpm. That is documentary pace, not explainer pace.
- Sentence gaps of 0.30–0.45 s; paragraph gaps of 0.7–1.2 s; longer, deliberate silences at "Illegal to move.", after "…at least one young man was killed.", and after "…one thousand and ninety-one."
