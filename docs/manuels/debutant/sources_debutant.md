# Sources et traçabilité — Manuel débutant

_Audit automatique généré depuis `fixtures_debutant.py` et `scan/scan_analysis_debutant.json`. Pour régénérer :_ `python3 scripts/regenerate_sources_doc.py`

## Vue d'ensemble

- **166 fixtures** au total, réparties sur 16 chapitres
- **152 CORPUS** (~91 %, extraites du livre Dubois)
- **12 GENERAL_KNOWLEDGE** (~7 %, reconstructions Claude depuis règles FMJD canoniques)
- **2 INVENTED** (~1 %, exemples pédagogiques ad-hoc, ch1-2 uniquement)
- **135** fixtures avec `final_move` reconstruit, **31** avec `final_move=None`
- **42** fixtures où Scan signale un gain forcé (éval `|·| ≥ 99`)
- **38** fixtures avec divergence Scan / `published_notation` (cf champ `notes` dans `scan_analysis_debutant.json`)

## Légende des colonnes

- **Source** : `CORPUS` = Dubois 2014 ; `GENERAL` = règles FMJD ; `INVENT` = exemple ad-hoc
- **Réf Dubois** : `source_ref` de la fixture (`dubois_apprent_combin_<page>_<diag>`)
- **`fm`** : statut du `final_move` reconstruit — `✓` présent, `∅` `None` (cf `claude_notes`)
- **Scan** : `✓` éval positive cohérente, `⚠` éval négative (trait adverse ou divergence), `🔴` divergence flaggée explicitement dans `notes`

## Chapitre 1

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH01_001` | GENERAL | `—` | ∅ | ✓ | — |
| `BEG_CH01_002` | GENERAL | `—` | ∅ | ✓ | — |

## Chapitre 2

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH02_001` | GENERAL | `—` | ∅ | ✓ | — |
| `BEG_CH02_002` | GENERAL | `—` | ∅ | ✓ | — |
| `BEG_CH02_003` | GENERAL | `—` | ✓ | 🔴 | 🔴 Forced move (no search). DIVERGENCE: published_notation starts with '31x22', Sca |
| `BEG_CH02_004` | GENERAL | `—` | ✓ | 🔴 | 🔴 Forced move (no search). DIVERGENCE: published_notation starts with '22x31', Sca |
| `BEG_CH02_005` | GENERAL | `—` | ✓ | 🔴 | 🔴 Forced move (no search). DIVERGENCE: published_notation starts with '31x11', Sca |
| `BEG_CH02_006` | GENERAL | `—` | ∅ | ✓ | — |
| `BEG_CH02_007` | INVENT | `—` | ✓ | 🔴 | 🔴 Forced move (no search). DIVERGENCE: published_notation starts with '38x18', Sca ; Position construite par Claude pour |
| `BEG_CH02_008` | GENERAL | `—` | ∅ | ✓ | — |
| `BEG_CH02_009` | GENERAL | `—` | ∅ | ✓ | — |
| `BEG_CH02_010` | GENERAL | `—` | ∅ | ✓ | — |
| `BEG_CH02_011` | INVENT | `—` | ∅ | ⚠ | Position construite par Claude pour illustrer la règle de non-soufflage. Le pion |
| `BEG_CH02_012` | GENERAL | `—` | ∅ | ✓ | — |

## Chapitre 3

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH03_001` | CORPUS | `dubois_apprent_combin_p6_d01` | ✓ | ✓ | — |
| `BEG_CH03_002` | CORPUS | `dubois_apprent_combin_p6_d02` | ✓ | ✓ | — |
| `BEG_CH03_003` | CORPUS | `dubois_apprent_combin_p6_d03` | ✓ | ✓ | — |
| `BEG_CH03_004` | CORPUS | `dubois_apprent_combin_p6_d04` | ✓ | ✓ | — |
| `BEG_CH03_005` | CORPUS | `dubois_apprent_combin_p6_d05` | ✓ | ✓ | Rafle 25x5 a deux trajectoires possibles aux captures identiques (cf RESOLUTIONS |
| `BEG_CH03_006` | CORPUS | `dubois_apprent_combin_p6_d06` | ✓ | ✓ | — |
| `BEG_CH03_007` | CORPUS | `dubois_apprent_combin_p6_d07` | ✓ | ✓ | — |
| `BEG_CH03_008` | CORPUS | `dubois_apprent_combin_p6_d08` | ✓ | ✓ | — |
| `BEG_CH03_009` | CORPUS | `dubois_apprent_combin_p6_d09` | ✓ | ✓ | ⚠️ Coquille PDF Dubois : le PDF source imprime '43-38' mais aucun blanc n'est en |
| `BEG_CH03_010` | CORPUS | `dubois_apprent_combin_p6_d10` | ✓ | ✓ | — |

## Chapitre 4

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH04_001` | CORPUS | `dubois_apprent_combin_p20_intro` | ✓ | ✓ | Exemple narratif d'introduction du chapitre 6 Dubois (page 20). Sert d'ouverture |
| `BEG_CH04_002` | CORPUS | `dubois_apprent_combin_p21_d01` | ✓ | ✓ | ⚠️ Coquille PDF : Dubois imprime '(15x21)', vraie notation '(15x31)' (typo 1er c |
| `BEG_CH04_003` | CORPUS | `dubois_apprent_combin_p21_d04` | ∅ | ✓ | Combinaison atypique : se termine par un coup simple (28-23), pas par une rafle. |
| `BEG_CH04_004` | CORPUS | `dubois_apprent_combin_p21_d06` | ✓ | ✓ | — |
| `BEG_CH04_005` | CORPUS | `dubois_apprent_combin_p21_d07` | ✓ | ✓ | — |
| `BEG_CH04_006` | CORPUS | `dubois_apprent_combin_p21_d09` | ✓ | ✓ | Combinaison emblématique : le « Coup royal » est un motif tactique nommé. Voir a |
| `BEG_CH04_007` | CORPUS | `dubois_apprent_combin_p21_d10` | ∅ | ✓ | ⚠️ Solution contient un envoi à dame intermédiaire et une rafle de dame ((49x24) |
| `BEG_CH04_008` | CORPUS | `dubois_apprent_combin_p24_d02` | ✓ | ✓ | — |
| `BEG_CH04_009` | CORPUS | `dubois_apprent_combin_p24_d05` | ∅ | ✓ | ⚠️ Idem D10 chap 6 : contient une rafle de dame non reconstructible par le modul |
| `BEG_CH04_010` | CORPUS | `dubois_apprent_combin_p24_d08` | ✓ | ✓ | ⚠️ Coquille PDF : Dubois imprime '31x3', vraie notation '32x3' (typo 2e chiffre  |
| `BEG_CH04_011` | CORPUS | `dubois_apprent_combin_p24_d09` | ✓ | ✓ | — |

## Chapitre 5

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH05_001` | CORPUS | `dubois_apprent_combin_p14_intro1` | ∅ | ✓ | Exemple narratif page 14. Contient une rafle de dame ((46x39)), non reconstructi |
| `BEG_CH05_002` | CORPUS | `dubois_apprent_combin_p14_intro2` | ∅ | ✓ | Exemple narratif page 14, deuxième position. Combinaison en 5 demi-coups, 3 phas |
| `BEG_CH05_003` | CORPUS | `dubois_apprent_combin_p15_d01` | ✓ | ✓ | — |
| `BEG_CH05_004` | CORPUS | `dubois_apprent_combin_p15_d02` | ✓ | ✓ | — |
| `BEG_CH05_005` | CORPUS | `dubois_apprent_combin_p15_d03` | ✓ | ✓ | — |
| `BEG_CH05_006` | CORPUS | `dubois_apprent_combin_p15_d05` | ✓ | ✓ | — |
| `BEG_CH05_007` | CORPUS | `dubois_apprent_combin_p15_d07` | ✓ | ✓ | — |
| `BEG_CH05_008` | CORPUS | `dubois_apprent_combin_p15_d08` | ∅ | ✓ | ⚠️ Solution contient une rafle de dame ((48x22)). final_move=None. Cf RESOLUTION |
| `BEG_CH05_009` | CORPUS | `dubois_apprent_combin_p15_d09` | ∅ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(13-19)', Scan PV starts with '13-19 ; ⚠️ Trait aux noirs. Combinaison où  |
| `BEG_CH05_010` | CORPUS | `dubois_apprent_combin_p15_d10` | ∅ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(14-19)', Scan PV starts with '14-19 ; ⚠️ Trait aux noirs. Envoi à dame du |

## Chapitre 6

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH06_001` | CORPUS | `dubois_apprent_combin_p17_intro` | ✓ | ✓ | Exemple narratif ouvrant le chapitre 5 Dubois. Illustre la méthode alternative à |
| `BEG_CH06_002` | CORPUS | `dubois_apprent_combin_p18_d01` | ✓ | ✓ | — |
| `BEG_CH06_003` | CORPUS | `dubois_apprent_combin_p18_d02` | ✓ | ✓ | — |
| `BEG_CH06_004` | CORPUS | `dubois_apprent_combin_p18_d03` | ✓ | ✓ | — |
| `BEG_CH06_005` | CORPUS | `dubois_apprent_combin_p18_d04` | ∅ | ✓ | Combinaison se terminant par un coup simple (38-32). final_move=None. |
| `BEG_CH06_006` | CORPUS | `dubois_apprent_combin_p18_d05` | ✓ | ✓ | — |
| `BEG_CH06_007` | CORPUS | `dubois_apprent_combin_p18_d06` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(17-21)', Scan PV starts with '17-21 ; ⚠️ Trait aux noirs. Partie historiq |
| `BEG_CH06_008` | CORPUS | `dubois_apprent_combin_p18_d07` | ✓ | ✓ | — |
| `BEG_CH06_009` | CORPUS | `dubois_apprent_combin_p18_d08` | ✓ | ✓ | Partie historique Bergsma-de Vries (DC Leeuwarden - Workum, 14-11-1961). |
| `BEG_CH06_010` | CORPUS | `dubois_apprent_combin_p18_d09` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(14-20)', Scan PV starts with '14-20 ; ⚠️ Trait aux noirs. Partie historiq |
| `BEG_CH06_011` | CORPUS | `dubois_apprent_combin_p18_d10` | ✓ | ✓ | — |

## Chapitre 7

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH07_001` | CORPUS | `dubois_apprent_combin_p26_intro1` | ✓ | ✓ | Exemple narratif ouvrant le chapitre 8 Dubois. |
| `BEG_CH07_002` | CORPUS | `dubois_apprent_combin_p26_intro2` | ∅ | ✓ | ⚠️ SOLUTION SUSPECTE — published_notation probablement corrompue (transcription  |
| `BEG_CH07_003` | CORPUS | `dubois_apprent_combin_p27_d01` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(14-20)', Scan PV starts with '14-20 |
| `BEG_CH07_004` | CORPUS | `dubois_apprent_combin_p27_d02` | ✓ | ✓ | Partie de Waard-Tjon A Ong (UTR-ch Hoofdklasse, 20-03-2013). |
| `BEG_CH07_005` | CORPUS | `dubois_apprent_combin_p27_d03` | ∅ | ✓ | Gambit : se termine par coup simple. final_move=None. |
| `BEG_CH07_006` | CORPUS | `dubois_apprent_combin_p27_d04` | ✓ | ✓ | — |
| `BEG_CH07_007` | CORPUS | `dubois_apprent_combin_p27_d05` | ✓ | ✓ | — |
| `BEG_CH07_008` | CORPUS | `dubois_apprent_combin_p27_d06` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(17-22)', Scan PV starts with '17-22 ; Partie Janssen-van Aalten (Huissen  |
| `BEG_CH07_009` | CORPUS | `dubois_apprent_combin_p27_d07` | ∅ | ✓ | ⚠️ Contient une rafle de dame ((48x30)). final_move=None. Partie Carli-van Outhe |
| `BEG_CH07_010` | CORPUS | `dubois_apprent_combin_p27_d08` | ✓ | ✓ | — |
| `BEG_CH07_011` | CORPUS | `dubois_apprent_combin_p27_d09` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(13-18)', Scan PV starts with '13-18 ; Partie Veresjagin-Balajan (URS-ch s |
| `BEG_CH07_012` | CORPUS | `dubois_apprent_combin_p27_d10` | ✓ | ✓ | Notation (ad lib) — le noir a 2 captures obligatoires équivalentes (cf RESOLUTIO |

## Chapitre 8

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH08_001` | CORPUS | `dubois_apprent_combin_p29_intro1` | ✓ | ✓ | Exemple narratif ouvrant le chap 9 Dubois. |
| `BEG_CH08_002` | CORPUS | `dubois_apprent_combin_p29_intro2` | ✓ | ✓ | Exemple narratif numéro 2 du chap 9 Dubois. |
| `BEG_CH08_003` | CORPUS | `dubois_apprent_combin_p30_d01` | ✓ | ✓ | Partie Linssen-Bandstra (NLD-chT Hoofdklasse, 02-10-1982). |
| `BEG_CH08_004` | CORPUS | `dubois_apprent_combin_p30_d02` | ✓ | ✓ | Rafle revenant sur sa case de départ (29x29). |
| `BEG_CH08_005` | CORPUS | `dubois_apprent_combin_p30_d03` | ✓ | ✓ | Partie Loenen-Hengefeld (Brunssum, 11-08-1990). |
| `BEG_CH08_006` | CORPUS | `dubois_apprent_combin_p30_d04` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(15-20)', Scan PV starts with '15-20 ; Trait aux noirs. Partie Badal-Kempe |
| `BEG_CH08_007` | CORPUS | `dubois_apprent_combin_p30_d05` | ✓ | ✓ | Partie Schippers-Barten (NLD-chT 2e klasse E, 14-01-2012). |
| `BEG_CH08_008` | CORPUS | `dubois_apprent_combin_p30_d06` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(3-9)', Scan PV starts with '3-9'. F ; Trait aux noirs. Partie van Leeuwen |
| `BEG_CH08_009` | CORPUS | `dubois_apprent_combin_p30_d07` | ✓ | ✓ | — |
| `BEG_CH08_010` | CORPUS | `dubois_apprent_combin_p30_d08` | ✓ | ✓ | — |
| `BEG_CH08_011` | CORPUS | `dubois_apprent_combin_p30_d09` | ✓ | ✓ | Partie Toet-Luteijn (Blokken RDG, 10-02-1977). Coup de talon, formation 31-36-37 |
| `BEG_CH08_012` | CORPUS | `dubois_apprent_combin_p30_d10` | ✓ | ✓ | — |

## Chapitre 9

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH09_001` | CORPUS | `dubois_apprent_combin_p42_d02` | ✓ | ✓ | Position centrale du chap 13 Dubois : le coup de l'express dans sa forme canoniq |
| `BEG_CH09_002` | CORPUS | `dubois_apprent_combin_p42_d03` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '33x2', Scan PV starts with '33x2x8x1 ; Position finale après rafle d'expre |
| `BEG_CH09_003` | CORPUS | `dubois_apprent_combin_p43_d01` | ✓ | ✓ | — |
| `BEG_CH09_004` | CORPUS | `dubois_apprent_combin_p43_d02` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(17-22)', Scan PV starts with '27-21 ; Trait aux noirs. Partie Grotenhuis  |
| `BEG_CH09_005` | CORPUS | `dubois_apprent_combin_p43_d03` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(23-29)', Scan PV starts with '39-34 ; Trait aux noirs. Partie Perot-Mosto |
| `BEG_CH09_006` | CORPUS | `dubois_apprent_combin_p43_d04` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(27-31)', Scan PV starts with '41-37 ; Trait aux noirs. Partie Ketelaars-K |
| `BEG_CH09_007` | CORPUS | `dubois_apprent_combin_p43_d05` | ✓ | ✓ | ✅ Coquille PDF Dubois corrigée. Le livre imprime '32-27 (23x21) 43-38 (29x40) 45 |
| `BEG_CH09_008` | CORPUS | `dubois_apprent_combin_p43_d06` | ✓ | ✓ | — |
| `BEG_CH09_009` | CORPUS | `dubois_apprent_combin_p43_d07` | ✓ | ✓ | — |
| `BEG_CH09_010` | CORPUS | `dubois_apprent_combin_p43_d08` | ✓ | ✓ | — |
| `BEG_CH09_011` | CORPUS | `dubois_apprent_combin_p43_d09` | ✓ | ✓ | Schéma canonique du coup de l'express. |
| `BEG_CH09_012` | CORPUS | `dubois_apprent_combin_p43_d10` | ✓ | ✓ | Variante du coup de l'express finissant en 4 plutôt qu'en 2. |

## Chapitre 10

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH10_001` | CORPUS | `dubois_apprent_combin_p45_d01` | ✓ | ✓ | Schéma canonique du coup de ricochet. |
| `BEG_CH10_002` | CORPUS | `dubois_apprent_combin_p45_d04` | ∅ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '27-22', Scan PV starts with '31-26'. ; Combinaison longue avec coup silenc |
| `BEG_CH10_003` | CORPUS | `dubois_apprent_combin_p46_d01` | ✓ | ✓ | — |
| `BEG_CH10_004` | CORPUS | `dubois_apprent_combin_p46_d02` | ✓ | ✓ | — |
| `BEG_CH10_005` | CORPUS | `dubois_apprent_combin_p46_d03` | ✓ | ✓ | — |
| `BEG_CH10_006` | CORPUS | `dubois_apprent_combin_p46_d04` | ✓ | ✓ | Partie Kloot-Kuipers (Ibis, 20-01-1939). |
| `BEG_CH10_007` | CORPUS | `dubois_apprent_combin_p46_d05` | ✓ | ✓ | — |
| `BEG_CH10_008` | CORPUS | `dubois_apprent_combin_p46_d06` | ✓ | ✓ | ✅ Coquille PDF Dubois corrigée. Le livre imprime '37-31 (26x28) 40-34 (30x39) 44 |
| `BEG_CH10_009` | CORPUS | `dubois_apprent_combin_p46_d07` | ✓ | ✓ | Coup Napoléon — préview du chap 13 manuel. |
| `BEG_CH10_010` | CORPUS | `dubois_apprent_combin_p46_d08` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(23-28)', Scan PV starts with '23-28 ; Trait aux noirs. Partie Coenen-van  |
| `BEG_CH10_011` | CORPUS | `dubois_apprent_combin_p46_d09` | ✓ | ✓ | — |
| `BEG_CH10_012` | CORPUS | `dubois_apprent_combin_p46_d10` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(15-20)', Scan PV starts with '15-20 ; Trait aux noirs. Partie Le Goff-Mol |

## Chapitre 11

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH11_001` | CORPUS | `dubois_apprent_combin_p48_d01` | ✓ | ✓ | Schéma 1 du coup de Rappel. |
| `BEG_CH11_002` | CORPUS | `dubois_apprent_combin_p48_d02` | ✓ | ✓ | Schéma 2 du coup de Rappel. |
| `BEG_CH11_003` | CORPUS | `dubois_apprent_combin_p48_d03` | ✓ | ✓ | Schéma 3 du coup de Rappel. |
| `BEG_CH11_004` | CORPUS | `dubois_apprent_combin_p49_d01` | ✓ | ✓ | — |
| `BEG_CH11_005` | CORPUS | `dubois_apprent_combin_p49_d02` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '22-17', Scan PV starts with '37-31'. |
| `BEG_CH11_006` | CORPUS | `dubois_apprent_combin_p49_d03` | ✓ | ✓ | — |
| `BEG_CH11_007` | CORPUS | `dubois_apprent_combin_p49_d04` | ✓ | ✓ | Combinaison + fin de partie. Sur (15-20), la lunette 19-14 est décisive. |
| `BEG_CH11_008` | CORPUS | `dubois_apprent_combin_p49_d05` | ✓ | ✓ | Préview coup de la Trappe (chap 18 manuel). Partie Michiels-Marini (BEL-ch, 1986 |
| `BEG_CH11_009` | CORPUS | `dubois_apprent_combin_p49_d06` | ✓ | ✓ | Préview coup de la Trappe (chap 18 manuel). |
| `BEG_CH11_010` | CORPUS | `dubois_apprent_combin_p49_d07` | ✓ | ✓ | Partie Rapopport-Gertsenzon (URS-chT, 03-06-1963). 4 demi-coups, plus complexe. |
| `BEG_CH11_011` | CORPUS | `dubois_apprent_combin_p49_d08` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(23-28)', Scan PV starts with '23-28 ; Trait aux noirs. Partie van Aalten- |
| `BEG_CH11_012` | CORPUS | `dubois_apprent_combin_p49_d09` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(22-27)', Scan PV starts with '22-27 ; Trait aux noirs. 7 demi-coups, stru |

## Chapitre 12

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH12_001` | CORPUS | `dubois_apprent_combin_p52_d01` | ✓ | ✓ | — |
| `BEG_CH12_002` | CORPUS | `dubois_apprent_combin_p52_d02` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(19-23)', Scan PV starts with '19-23 ; Trait aux noirs. Partie Datel-Schwa |
| `BEG_CH12_003` | CORPUS | `dubois_apprent_combin_p52_d03` | ✓ | ✓ | — |
| `BEG_CH12_004` | CORPUS | `dubois_apprent_combin_p52_d04` | ✓ | ✓ | Partie Gordijn-den Hartogh (Damas, 1952). |
| `BEG_CH12_005` | CORPUS | `dubois_apprent_combin_p52_d05` | ✓ | ✓ | Préview coup de la Trappe. Partie Clasquin-van Es (Alblasserdam 1981). |
| `BEG_CH12_006` | CORPUS | `dubois_apprent_combin_p52_d06` | ✓ | ✓ | — |
| `BEG_CH12_007` | CORPUS | `dubois_apprent_combin_p52_d07` | ✓ | ✓ | — |
| `BEG_CH12_008` | CORPUS | `dubois_apprent_combin_p52_d08` | ∅ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '26-21', Scan PV starts with '39-33'. ; Partie Bergsma-Spoelstra (Gezellig  |
| `BEG_CH12_009` | CORPUS | `dubois_apprent_combin_p52_d09` | ∅ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(15-20)', Scan PV starts with '15-20 ; Trait aux noirs. Partie Spoelstra-B |
| `BEG_CH12_010` | CORPUS | `dubois_apprent_combin_p52_d10` | ✓ | ✓ | Combinaison fulgurante à 5 demi-coups. |

## Chapitre 13

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH13_001` | CORPUS | `dubois_apprent_combin_p55_d01` | ∅ | ✓ | ⚠️ Envoi à dame du noir (rafle 49x24). final_move=None (R007). |
| `BEG_CH13_002` | CORPUS | `dubois_apprent_combin_p55_d02` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(23-28)', Scan PV starts with '13-18 ; Trait aux noirs. Partie Bom-van Dij |
| `BEG_CH13_003` | CORPUS | `dubois_apprent_combin_p55_d03` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(24-30)', Scan PV starts with '24-30 ; Trait aux noirs. Partie Baerends-St |
| `BEG_CH13_004` | CORPUS | `dubois_apprent_combin_p55_d04` | ✓ | ✓ | ✅ Coquille PDF Dubois corrigée. Le livre imprime '(18x27)' (les opérandes invers |
| `BEG_CH13_005` | CORPUS | `dubois_apprent_combin_p55_d05` | ✓ | ✓ | Partie Haijtink-Scholte Lubberink (NLD-chT Hoofdklasse, 1994). |
| `BEG_CH13_006` | CORPUS | `dubois_apprent_combin_p55_d06` | ✓ | ✓ | Partie van Leijen-Schunselaar (NLD-chT Hoofdklasse 1971). |
| `BEG_CH13_007` | CORPUS | `dubois_apprent_combin_p55_d07` | ✓ | ✓ | Coup Napoléon pur. |
| `BEG_CH13_008` | CORPUS | `dubois_apprent_combin_p55_d08` | ✓ | ✓ | Partie Kolodiev-Weytsman (URS-ch, 1973). |
| `BEG_CH13_009` | CORPUS | `dubois_apprent_combin_p55_d09` | ✓ | ✓ | Forme canonique du coup Napoléon. |
| `BEG_CH13_010` | CORPUS | `dubois_apprent_combin_p55_d10` | ✓ | ✓ | Partie Papinski-Lewandowski (Poczesna, 1979). |

## Chapitre 14

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH14_001` | CORPUS | `dubois_apprent_combin_p58_d01` | ✓ | ✓ | — |
| `BEG_CH14_002` | CORPUS | `dubois_apprent_combin_p58_d02` | ✓ | ✓ | Révision du coup de Rappel. |
| `BEG_CH14_003` | CORPUS | `dubois_apprent_combin_p58_d03` | ✓ | ✓ | — |
| `BEG_CH14_004` | CORPUS | `dubois_apprent_combin_p58_d04` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(16-21)', Scan PV starts with '16-21 ; Trait aux noirs. Partie Kocken-Doom |
| `BEG_CH14_005` | CORPUS | `dubois_apprent_combin_p58_d05` | ✓ | ✓ | Partie Hoogland-van den Broek (Wch, 1912). 7 demi-coups. |
| `BEG_CH14_006` | CORPUS | `dubois_apprent_combin_p58_d06` | ✓ | ✓ | Forme canonique du coup de la Trappe. |
| `BEG_CH14_007` | CORPUS | `dubois_apprent_combin_p58_d07` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '29-24', Scan PV starts with '43-38'. ; Partie Maertzdorf-Alofs (NLD-chT 2e |
| `BEG_CH14_008` | CORPUS | `dubois_apprent_combin_p58_d08` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(20-24)', Scan PV starts with '20-24 ; Trait aux noirs. Partie Bronstring- |
| `BEG_CH14_009` | CORPUS | `dubois_apprent_combin_p58_d09` | ✓ | ✓ | — |
| `BEG_CH14_010` | CORPUS | `dubois_apprent_combin_p58_d10` | ∅ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(14-20)', Scan PV starts with '14-20 ; Trait aux noirs. Contient une rafle |

## Chapitre 15

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH15_001` | CORPUS | `dubois_apprent_combin_p61_d01` | ✓ | ✓ | Coup de mazette + talon. Note : la notation Dubois indique (19x19) — probable ty |
| `BEG_CH15_002` | CORPUS | `dubois_apprent_combin_p61_d02` | ✓ | ✓ | — |
| `BEG_CH15_003` | CORPUS | `dubois_apprent_combin_p61_d03` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '27-21', Scan PV starts with '27-22'. ; Partie Lewkowicz-Blokland (NLD-chT  |
| `BEG_CH15_004` | CORPUS | `dubois_apprent_combin_p61_d04` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '34-29', Scan PV starts with '33-29'. ; Pur coup de talon. |
| `BEG_CH15_005` | CORPUS | `dubois_apprent_combin_p61_d05` | ✓ | ✓ | Pur coup de talon, symétrique du D4. |
| `BEG_CH15_006` | CORPUS | `dubois_apprent_combin_p61_d06` | ✓ | ✓ | Partie Vatutin-Steijlen (NLD-chT Ereklasse, 2007). |
| `BEG_CH15_007` | CORPUS | `dubois_apprent_combin_p61_d07` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(7-12)', Scan PV starts with '7-12'. ; Trait aux noirs. Partie Wiering-Sie |
| `BEG_CH15_008` | CORPUS | `dubois_apprent_combin_p61_d08` | ✓ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(7-12)', Scan PV starts with '7-12'. ; Trait aux noirs. Partie Depaepe-Gro |
| `BEG_CH15_009` | CORPUS | `dubois_apprent_combin_p61_d09` | ✓ | ✓ | — |
| `BEG_CH15_010` | CORPUS | `dubois_apprent_combin_p61_d10` | ✓ | ✓ | Partie de Jongh-Bizot (Parijs, 1927). |

## Chapitre 16

| Fixture | Source | Réf Dubois | `fm` | Scan | Notes |
|---|---|---|---|---|---|
| `BEG_CH16_001` | CORPUS | `dubois_apprent_combin_p64_d01` | ∅ | ✓ | ⚠️ Contient un envoi à dame du noir avec rafle de dame (48x33). final_move=None  |
| `BEG_CH16_002` | CORPUS | `dubois_apprent_combin_p64_d02` | ✓ | ✓ | Partie Dartelen-Ligthart (NLD-ch, 1938). |
| `BEG_CH16_003` | CORPUS | `dubois_apprent_combin_p64_d03` | ✓ | ✓ | — |
| `BEG_CH16_004` | CORPUS | `dubois_apprent_combin_p64_d04` | ✓ | ✓ | Partie Davidov-Romanov (URS-chT, 1963). |
| `BEG_CH16_005` | CORPUS | `dubois_apprent_combin_p64_d05` | ✓ | ✓ | Combinaison piégeuse — la voie évidente échoue. |
| `BEG_CH16_006` | CORPUS | `dubois_apprent_combin_p64_d06` | ✓ | ✓ | Partie Leijenaar-Romanskaia (Olympiade jr, 2003). |
| `BEG_CH16_007` | CORPUS | `dubois_apprent_combin_p64_d07` | ✓ | ✓ | Coup de mazette — autre coup nommé que Dubois introduit ici. |
| `BEG_CH16_008` | CORPUS | `dubois_apprent_combin_p64_d08` | ∅ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '(14-19)', Scan PV starts with '14-19 ; Trait aux noirs. Envoi à dame blanc |
| `BEG_CH16_009` | CORPUS | `dubois_apprent_combin_p64_d09` | ∅ | 🔴 | 🔴 DIVERGENCE: published_notation starts with '34x23', Scan PV starts with '32-28'. ; ⚠️ Envoi à dame noir avec rafle de  |
| `BEG_CH16_010` | CORPUS | `dubois_apprent_combin_p64_d10` | ∅ | ✓ | Partie Aliar-Huijzer (Arnhem-ch, 2010). Notation Dubois '30.48x6' anomalie — var |

---

_Régénération : ce doc est dérivé. Source de vérité : `docs/pre_process_corpus/fixtures_debutant.py` (champs `source`, `source_ref`, `crop_id`, `final_move`, `claude_notes`) et `docs/pre_process_corpus/scan/scan_analysis_debutant.json` (champs `eval_after_pv`, `notes`)._