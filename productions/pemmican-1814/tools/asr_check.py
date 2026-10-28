"""Transcribe each narration sentence with Whisper small.en (sherpa-onnx) and report word error rate."""
import sys, json, re, sherpa_onnx, soundfile as sf, librosa, numpy as np
mdir, meta_path, wavdir = sys.argv[1:4]
rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=f"{mdir}/small.en-encoder.int8.onnx",
        decoder=f"{mdir}/small.en-decoder.int8.onnx", tokens=f"{mdir}/small.en-tokens.txt", num_threads=4)
meta = json.load(open(meta_path))
NUM = {"1811":"eighteen eleven","1812":"eighteen twelve","1813":"eighteen thirteen","1814":"eighteen fourteen",
       "1815":"eighteen fifteen","1816":"eighteen sixteen","1821":"eighteen twenty one","1840":"eighteen forty",
       "1870s":"eighteen seventies","1879":"eighteen seventy nine","1889":"eighteen eighty nine","1911":"nineteen eleven",
       "2014":"twenty fourteen","22":"twenty two","20":"twenty","479":"four hundred and seventy nine","1,091":"one thousand and ninety one"}
def norm(s):
    s = s.lower().replace("-", " ").replace("é","e").replace("î","i").replace("â","a").replace("è","e")
    for k,v in NUM.items(): s = s.replace(k, v)
    s = re.sub(r"[^a-z' ]", " ", s)
    return s.split()
def wer(r, h):
    d = np.zeros((len(r)+1, len(h)+1), int); d[:,0]=range(len(r)+1); d[0,:]=range(len(h)+1)
    for i in range(1,len(r)+1):
        for j in range(1,len(h)+1):
            d[i,j]=min(d[i-1,j]+1,d[i,j-1]+1,d[i-1,j-1]+(r[i-1]!=h[j-1]))
    return d[-1,-1]/max(1,len(r))
tot_e=tot_n=0; rows=[]
for fn in sorted(meta):
    a, sr = sf.read(f"{wavdir}/{fn}", dtype="float32")
    a = librosa.resample(a, orig_sr=sr, target_sr=16000)
    s = rec.create_stream(); s.accept_waveform(16000, a); rec.decode_stream(s)
    hyp = s.result.text.strip(); r=norm(meta[fn]["text"]); h=norm(hyp); w=wer(r,h)
    tot_e += w*len(r); tot_n += len(r)
    meta[fn]["asr"] = hyp; meta[fn]["wer"] = round(w,3)
    if w > 0: rows.append((round(w,2), fn, meta[fn]["text"], hyp))
json.dump(meta, open(meta_path,"w"), indent=1, ensure_ascii=False)
print("overall WER %.3f over %d words" % (tot_e/tot_n, tot_n))
for r in sorted(rows, reverse=True): print(r)
