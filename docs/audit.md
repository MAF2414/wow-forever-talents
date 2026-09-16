# Client data audit — September 16, 2026

**Result:** All 42 cached Forever source tables match an independent extraction
from Blizzard's client archives for **1.60.1.69876**. The comparison covered
**243,982 records and 3,685,417 fields**, with no missing or additional records
and no field differences beyond floating-point serialization tolerance.

This verifies packaged client data. It is not a logged-in gameplay test.

## Method

- Confirmed the build against Blizzard's public
  [wow_classic_beta manifest](https://us.version.battle.net/v2/products/wow_classic_beta/versions).
- Read the client root and encoding manifests, located files by FileDataID,
  and extracted 51 DB2 files from Blizzard's CDN archives using CASCLib.
  The decoded files total approximately 9.6 MB; no full game installation was needed.
- Parsed DB2 files independently with DBCD and WoWDBDefs. Compared every record
  and field in the 42 original CSV tables, flattening array columns and resolving
  the anonymous SkillLineAbility/TraitCurrency column names. Floating-point
  comparisons use relative and absolute tolerance of 0.000001; strings and IDs
  must match. Line-ending differences are ignored.
- Inspected nine additional tables covering entry conditions, talent costs,
  currency sources and default loadouts. The entry-condition, per-node/per-entry
  cost override and default-loadout tables are empty in this snapshot.
- Checked the class-to-tree assignments, every regular node's position and point
  threshold, all talent rank curves, prerequisite links, and the complete
  one-to-one coverage of both talent snapshots in the comparison.
- Checked representative browser interactions and added regression checks for
  the corrections below.

[Table counts, FileDataIDs and SHA-256 hashes](client-audit.json)

Build config: `e7fab7248766e9e7daddb3b6083c9c3c`  
Root content key: `eeee5a6e1cf0652a5b459e2b37f6b57f`

Tool source revisions:

- [CASCLib](https://github.com/WoW-Tools/CascLib/tree/3f8be478177802de4ae7ebae24fb25ab860ef104)
- [DBCD](https://github.com/wowdev/DBCD/tree/2d50ae2633166ff5dd57e802e960f5e9e558177f)
- [Forever UI source](https://github.com/Gethe/wow-ui-source/tree/f0da0a9171aa736c8a64d2b3a8ae70195f5d2afb)

The local CASCLib copy uses HTTPS CDN URLs and predownloaded archive indexes.
BLTE data validation remains enabled. DB2 schemas are recorded by SHA-256
in the machine-readable report.

## Corrections made

- Unlimited duration now displays **Unlimited**, instead of `-0.001` seconds.
- Explicit `$m` minimum and `$M` maximum expressions retain their distinct
  bounds. General `$s` amounts and numeric effect comparisons still use means.
- Classic prerequisite ranks are retained and displayed, including rank 3 of
  Critical Mass for Combustion.
- Multiple sufficient connections are labelled as alternatives. In particular,
  the two incoming Intimidation links are not both mandatory.
- Venom's additional mixed node/group condition is preserved with an explicit
  uncertainty note. It is not silently reduced to a general point threshold.
- Talent comparison cards now also display prerequisites and the base-value
  caveat for damage and healing.

## Remaining limits

- The Classic baseline remains the pre-SoD **1.14.4.51395** CSV snapshot. The
  independent CDN extraction described above covers Forever, not that older
  Classic build.
- Three Forever nodes have out-of-grid coordinates; they remain separate.
  One Hunter connection runs backwards in the source data and remains marked.
- Nine regular Forever talent descriptions retain unresolved client expressions.
  They are flagged and their original text is available. Character stats,
  level-dependent formulas and conditional client text are not fully simulated.
- Cutthroat has five ranks, but its secondary effect curve has explicit points
  only for ranks 1–3. The displayed proc chance uses a different, complete curve.
  The secondary effect's behavior at ranks 4–5 remains unverified and is marked.
- Server hotfixes, learnability, availability, trainer rules and live combat
  behavior cannot be confirmed by these packaged files alone.
- Class spells are assignments from the selected class skill lines, not a
  verified character spellbook. Inherited seasonal entries remain separated.
- “Unchanged” means unchanged in the compared fields. Triggered subspell chains
  and every possible spell attribute are not recursively compared.
