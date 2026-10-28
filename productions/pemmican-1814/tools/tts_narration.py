"""Generate the narration with Kokoro-82M (kokoro-onnx), one sentence at a time.

Usage: python3 tts_narration.py <model_dir> <narration.txt> <out_dir> [--only P01,P02] [--speed 0.94]

Writes out_dir/sentences/<Pxx>_<n>.wav (24 kHz mono) and out_dir/sentences.json
with the text, phonemes and duration of every sentence. Assembly into a timed
track (with pauses) is done by assemble_narration.py.
"""
import argparse, json, os, re, sys
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from kokoro_onnx.tokenizer import Tokenizer

VOICE = "af_heart"
LANG = "en-us"

# Spoken forms for numbers that espeak would otherwise read digit-group by digit-group.
SPOKEN = {
    "1811": "eighteen eleven", "1812": "eighteen twelve", "1813": "eighteen thirteen",
    "1814": "eighteen fourteen", "1815": "eighteen fifteen", "1816": "eighteen sixteen",
    "1821": "eighteen twenty-one", "1840": "eighteen forty", "1870s": "eighteen seventies",
    "1879": "eighteen seventy-nine", "1889": "eighteen eighty-nine", "1911": "nineteen eleven",
    "2014": "twenty fourteen",
}

# Phoneme corrections: (wrong espeak output, corrected IPA). Verified with Whisper ASR.
PHONEME_FIX = [
    ("mˈeɪɾiz", "meɪtˈiː"),                 # Métis -> may-TEE
    ("məkdˈoʊnəl", "məkdˈɑːnəl"),            # Macdonell -> mac-DON-ell
    ("sˈaʊɚɹˌɪs", "sˈʊɹɪs"),                 # Souris -> SOOR-iss
    ("kwæpˈɛl", "kəpˈɛl"),                   # Qu'Appelle -> kuh-PELL
    ("ɡɹˈɛnuːˌɪlɚ", "ɡɹɛnuːjˈɛɹ"),           # Grenouillère -> gren-oo-YAIR
    ("lˌæ ɡɹ", "lɑː ɡɹ"),                    # "la" before Grenouillère
    ("vˈɪktwɑːɹ", "viktwˈɑːɹ"),              # Victoire
    ("lˌæ vi", "lɑː vi"),
    ("pˈɪmɪhkən", "pɪmˈiːhkɑːn"),            # pimîhkân -> pih-MEE-kahn
    ("ˈæθɐbˌæskə", "æθəbˈæskə"),             # Athabasca -> ath-uh-BASK-uh
    ("ɑːdʒˈɪbwi", "oʊdʒˈɪbweɪ"),             # Ojibwe -> oh-JIB-way
    ("pˌɪɪkˈɑːni", "piːkˈɑːni"),             # Piikani -> pee-KAH-nee
    ("sˈɪksɪkə", "sɪksˈɪkə"),                # Siksika -> sik-SIK-uh
    ("ˈæmʌndsən", "ˈɑːmənsən"),              # Amundsen -> AH-mun-sen
    ("pɪˈɛɹ fˈælkən", "pjˈɛɹ fˈælkən"),       # Pierre Falcon
    ("sˈɛlkɜːk", "sˈɛlkɚk"),                 # Selkirk (rhotic; ɝ variant was heard as "Selk")
]


def normalize(text):
    for k, v in sorted(SPOKEN.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(rf"\b{k}\b", v, text)
    return text


def split_sentences(par):
    # Keep short emphatic fragments ("Frog Plain.") as their own sentences.
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", par.strip())
    return [p.strip() for p in parts if p.strip()]


def read_paragraphs(path):
    out = []
    for line in open(path, encoding="utf-8"):
        if "|" in line:
            pid, txt = line.split("|", 1)
            out.append((pid.strip(), txt.strip()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dir"); ap.add_argument("narration"); ap.add_argument("out_dir")
    ap.add_argument("--only", default=""); ap.add_argument("--speed", type=float, default=0.82)
    a = ap.parse_args()
    os.makedirs(f"{a.out_dir}/sentences", exist_ok=True)
    k = Kokoro(f"{a.model_dir}/kokoro-v1.0.onnx", f"{a.model_dir}/voices-v1.0.bin")
    tok = Tokenizer()
    only = set(x for x in a.only.split(",") if x)
    meta_path = f"{a.out_dir}/sentences.json"
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    for pid, par in read_paragraphs(a.narration):
        if only and pid not in only:
            continue
        for i, sent in enumerate(split_sentences(par)):
            ph = tok.phonemize(normalize(sent), LANG)
            for wrong, right in PHONEME_FIX:
                ph = ph.replace(wrong, right)
            audio, sr = k.create(ph, voice=VOICE, speed=a.speed, lang=LANG, is_phonemes=True)
            fn = f"{pid}_{i:02d}.wav"
            sf.write(f"{a.out_dir}/sentences/{fn}", audio, sr)
            meta[fn] = {"pid": pid, "idx": i, "text": sent, "phonemes": ph,
                        "dur": round(len(audio) / sr, 3), "sr": sr}
            print(fn, meta[fn]["dur"], sent[:60], flush=True)
    json.dump(meta, open(meta_path, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
