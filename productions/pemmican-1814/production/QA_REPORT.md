# QA Report — The Pemmican War

## 1. Editorial QA: every on-screen claim vs research/FACT_CHECK.md

| On screen | Fact row | Status |
|---|---|---|
| "about three-quarters water" (raw lean meat), 74/100 squares | A3b | ✅ USDA values 74–75 g/100 g |
| *pimîhkân*, Cree; built on *pimiy* "fat, grease" | A3 | ✅ |
| 5–6 lb fresh lean meat → 1 lb dried, pounded | A7 | 🟡 sourced ratio, labelled "reported in fur-trade era accounts" |
| Fat ≈ 9 kcal/g, protein ≈ 4 kcal/g | A10 | ✅ Atwater factors, labelled |
| ≈ 2 lb of pemmican a day for a working man | A11 | 🟡 labelled "fur-trade reckoning; actual rations varied" |
| Crew of six, perhaps 35 miles a day; 4 × 90 lb = 360 lb; next depot hundreds of miles on | B3, B3a | 🟡 sourced; the inconsistent "two weeks" line was removed and re-voiced |
| ≈ 3,000 miles; Montreal crews / interior crews meeting at Fort William | B1, B2 | ✅ route marked "simplified" |
| Assiniboia ≈ 116,000 sq mi; Italy at the same scale | C1 | ✅ boundary marked "approximate"; polygon scaled to 300,000 km² |
| Order of 8 Jan 1814: one year; meat, fish, grain, vegetables; licence; seized and paid for | C4 | ✅ shown as a paraphrase, labelled "not the original wording" |
| 479 bags; 479 × 90 lb ≈ 43,000 lb; kegs of fat, dried meat | C6 | 🟡 sourced; arithmetic checked (43,110 lb) |
| Timeline: 1812 arrival; Jan 1814 order; 1814 Souris; June 1815 departure; fall 1815 Semple; Mar 1816 Fort Gibraltar; spring 1816 Qu'Appelle; 19 June 1816 Frog Plain | C-, D-rows | ✅ (Qu'Appelle shown as "spring", as sources disagree on the day) |
| Seven Oaks Massacre (settler tradition) / Victory of Frog Plain, *la Victoire de la Grenouillère* (Métis) | D7 | ✅ both memories, no side taken |
| Pierre Falcon, Métis songwriter, *La Chanson de la Grenouillère* | D8 | ✅ |
| Fort William seized by Selkirk, August 1816 | E1 | ✅ |
| 1821 merger under the HBC name | E3 | ✅ |
| 1,210 carts on the 1840 hunt, as counted by Alexander Ross | E5 | ✅ |
| Amundsen's party: pemmican with oatmeal and dried peas; South Pole 1911 | E6 | ✅ |
| "Tens of millions — estimates vary widely; nobody knows exactly" | F1 | ⚠️ presented as an estimate |
| 1879, Canadian plains | F5 | ✅ |
| 1,091 bison, Hornaday's 1889 count | F2 | ✅ |
| Buffalo Treaty 2014, Browning, Montana; Blackfeet, Blood Tribe (Kainai), Piikani, Siksika; first treaty among them in 150+ years | F8 | ✅ "four of the signatory nations shown; others also signed" |
| Lower thirds: Selkirk (HBC shareholder), Macdonell (governor), Semple (governor from fall 1815), Grant (Métis leader), Hornaday (naturalist) | C2, C3, C-/D-rows, F2 | ✅ no unverified birth/death years used |

Representation checks: Indigenous peoples are named specifically (Cree, Assiniboine/Nakoda, Métis, Blackfeet, Kainai,
Piikani, Siksika). Homelands map carries "approximate; other nations also lived and traded across this region".
No people are depicted in reconstructions. The battle is not depicted; the edit cuts to silence.

Honesty checks: every 3D sequence family carries a "Reconstruction" tag at first appearance; credits and description
state the synthetic voice, illustrative reconstructions and generated props. No AI image or video generation used.

## 2. Technical QA — `delivery/The_Pemmican_War_1080p.mp4` (tools/qa.py + ffmpeg, 2026-10-29)

| Check | Result | Status |
|---|---|---|
| Container / video | MP4, H.264 High, yuv420p, BT.709, 1920×1080, 30 fps constant, 27,000 frames, 15:00.000 | ✅ |
| Encoding | x264 CRF 18 (preset medium), 2 s GOP; 1.47 GB, ≈13.1 Mb/s | ✅ |
| Audio | AAC-LC 320 kb/s, 48 kHz, stereo, 14:59.989 (A/V durations match) | ✅ |
| Decode errors (`ffmpeg -v error -f null`) | none | ✅ |
| Black frames (`blackdetect`) | 3 segments, all intended: dip into chapter IV (8:42.6, 0.43 s), cut to credits (14:44.9, 0.43 s), final fade (14:59.3) | ✅ |
| Frozen picture (`freezedetect`) | 0 events | ✅ |
| Silence > 1.5 s (`silencedetect`) | none (the post-battle silence is an intended near-silent ambience, not dead air) | ✅ |
| Loudness (EBU R128) | −14.1 LUFS integrated, −1.3 dBTP, LRA 3.4 LU | ✅ YouTube-ready |
| Subtitles | 235 cues, 2,065 words = narration word count, sentence starts aligned to narration timing (max offset 0.0 s), no overlaps, ≤ 42 characters per line, last cue 14:44.0 | ✅ |
| Chapters | 0:00 · 1:09 · 3:33 · 6:27 · 8:39 · 11:43 · 14:45, checked against rendered frames | ✅ |
| Short | 1080×1920, 30 fps, 58.5 s, H.264 + AAC 48 kHz stereo, −14.1 LUFS, −1.5 dBTP | ✅ |

## 3. Visual QA

Method: a contact sheet of the finished MP4 (one frame every 15 s, 60 frames), full-resolution frames of every
re-rendered plate in context, and frame grabs at every chapter boundary. This is sampled-frame inspection,
not real-time viewing: the film was never watched as moving picture with sound by a person in this environment.

Defects found by this QA and fixed before the final render:

| Defect | Cause | Fix |
|---|---|---|
| Storehouse close-up (3:12, 9:37) nearly black (mean level 1.6 %) | the doorway bounce light pointed out of the door | light turned into the room; S1 and S2 re-rendered (S2 at 32 samples) |
| Pale "lake" under the bison herd, the sunset herd and the cart line | flat far-ground sheet at −1 m flooded hollows of the rolling terrain (down to −4 m) | sheet moved to −6 m; B1–B3 re-rendered |
| Dark band under the winter palisade; black strip under the summer palisade | foreground pass showed the buried parts of drifts and pickets | background objects rendered as holdouts in the fort foreground pass |
| Summer fort foreground washed out and streaky | sparse grass spread over an area mostly outside the frame; strong frontal fill; backlit ground sheen | dense grass only where the camera sees it, softer fill, low ground specular |
| Speckle noise in the defocused oaks of the grass close-up | 16-sample render of shallow depth of field | constant soft blur on that layer (it is out of focus anyway) |
| Chimney and lodge smoke invisible | smoke too thin and too close to the sky's brightness | denser, darker plumes |
| Short: captions unreadable over snow; end-card title wider than the frame | white text on white; type size for landscape | dark caption plate; smaller title |

Known limitations (not fixed, judged acceptable): bison are seen as backlit silhouettes at telephoto distance and
hold still (the motion comes from grass, light and camera); the 3D look is a stylised reconstruction and is labelled
"Reconstruction" throughout; one oak in the Frog Plain wide shot has an arched limb that reads slightly odd.

## 4. Audio QA

Measured: loudness, true peak and LRA above; narration −17.8 LUFS in the mix; music under speech −32.7 LUFS and
−25.6 LUFS in pauses (ducking −7.5 dB music, −5 dB ambience); no clipping. Difficult names get corrected phonemes in
`tools/tts_narration.py`, following the pronunciation guide (Métis, Macdonell, Souris, Qu'Appelle, Grenouillère,
*pimîhkân*, Athabasca, Ojibwe, Piikani and others). The narration was transcribed back with Whisper (small.en):
overall word error rate ≈ 4 %, with the differences in formatting (numbers, hyphens). ASR shows the English is
intelligible; it cannot certify how the Cree and French terms sound. Naturalness and emphasis were judged from
these measurements only, so a human listening pass before publishing is recommended.

## 5. Version 2: archival pass (2026-10-29)

**What changed:** 14 archival clips (about 111 s, 12% of the running time) from Smithsonian Open Access (CC0) replace
3D shots of bison, camps, the canoe road, the fur-trade post and the hide-trade era; see ASSET_MANIFEST §1b and
FACT_CHECK §J. Sound for those shots was re-laid (place beds, hoofbeats under the Muybridge loop). Picture timing,
narration, subtitles and chapters are unchanged.

| Check (tools/qa.py + ffmpeg) | Result |
|---|---|
| Video | H.264 High, 1920×1080, 30 fps, 27,000 frames, 15:00.000, BT.709 |
| Audio | AAC 48 kHz stereo, 14:59.989 |
| Decode errors | none |
| Black frames | 3, all intended (8:42.6 chapter dip, 14:44.9 to credits, final fade) |
| Frozen picture / silence over 1.5 s | 0 / none |
| Loudness | −14.1 LUFS, −1.5 dBTP, LRA 3.4 LU |
| Subtitles | 235 cues, 2,065 words (= narration), no overlaps, at most 42 characters per line |
| Rendering | 15 of 45 chunks re-rendered; 30 unchanged ones verified by an edit signature |

Visual check (sampled frames, every 15 s plus the new clips at full resolution): every archival image carries its
credit (title, date, maker, collection), none is cropped outside the image, the Muybridge print loops through eight
views and fades out, the Hornaday photographs sit under the 1,091 counter and the lower third without collision.
Not verified: real-time playback and sound by a person.

Still weak (not fixed in this pass): Frog Plain oaks and grass (about 85 s), the summer and winter fort, the dock and
rawhide bag macros, the berry bowl at 13:55 (reads as dark blobs), the prairie lodges and cart line, and distant
bison silhouettes that stand still. These are 3D shots with no authentic image available from the Smithsonian
collection; see PRODUCTION_STATUS "Next step".
