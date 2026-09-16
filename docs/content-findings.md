# Sets, instances and bosses — September 17, 2026

Client **1.60.1.69876**, compared with Classic **1.14.4.51395** and SoD **1.15.9.69722**.

[Open the searchable findings](https://maf2414.github.io/wow-forever-talents/content.html).

Independent CDN extraction: **15 tables, 35,913 rows, 2,193,448 compared fields**. All ten nonempty tables match the CSV exports. Five journal tables are present but empty.

## Findings

51 set IDs are absent from both baselines: 18 Tier 1 class/role sets, 26 PvP-named variants and seven other sets. A new ID is not proof of a new appearance or an obtainable reward.

80 sets sharing a Classic ID have changed names, item membership, bonus spell links or resolved bonus text. The viewer includes the Classic bonuses. This is not a full comparison of item stats or triggered effects.

The 18 Tier 1 sets have six member IDs each and four linked bonuses at 2, 3, 4 and 5 pieces. Their spell names explicitly say Tier 1. All 108 referenced tier-item IDs lack ItemSparse metadata in this snapshot; exact item stats, drop sources and raid assignments remain unverified.

## Tier 1 class sets

| Class / role | Set | 5-piece bonus |
|---|---|---|
| Mage | Manaflare Regalia | Your Frostfire Bolt spell has a 10% increased chance to trigger Missile Barrage, gains 10% increased critical strike chance while your Combustion spell is active, and has a 10% increased chance to trigger Fingers of Frost. |
| Rogue | Grimstitch Armor | Reduces the cost of your Envenom and Eviscerate abilities by 5 Energy. |
| Warlock | Demonheart Raiment | Your Life Tap generates 20% more Mana at no additional Health cost. |
| Hunter | Wildstalker Armor | Reduces the cooldown on your Aimed Shot and Multi-Shot abilities by 1 sec. |
| Warrior - Arms/Fury | Battlegear of Glory | Reduces the cooldown on your Recklessness ability by 30 sec. |
| Warrior - Protection | Battleplate of Glory | Reduces the cooldown on your Shield Wall ability by 30 sec. |
| Priest - Discipline/Holy | Vestments of Conviction | Reduces the cooldown on your Penance and Prayer of Mending spells by 1 sec. |
| Priest - Shadow | Raiments of Conviction | Reduces the cooldown on your Devouring Plague spell by 60 sec. |
| Paladin - Retribution | Justice Battlegear | Reduces the cooldown on your Judgement spell by 0.5 sec. |
| Paladin - Holy | Justice Armor | Reduces the cooldown on your Holy Shock spell by 1 sec. |
| Paladin - Protection | Justice Battleplate | Reduces the duration of Forbearance any time you gain it by 10 sec. |
| Shaman - Restoration | The Spiritcaller | Reduces the cooldown on your Riptide spell by 1 sec. |
| Shaman - Enhancement | The Spiritcaller's Rage | Reduces the cooldown on your Stormstrike ability by 0.5 sec. |
| Shaman - Elemental | The Spiritcaller's Storm | Reduces the cooldown on your Lava Burst spell by 1 sec. |
| Druid - Restoration | Grovekeeper Raiment | Reduces the cooldown on your Swiftmend spell by 3 sec. |
| Druid - Guardian | Grovekeeper Rage | Reduces the cooldown on your Berserk ability by 15 sec. |
| Druid - Balance | Grovekeeper Eclipse | Increases the duration of your Insect Swarm spell by 3 sec. |
| Druid - Feral | Grovekeeper Ferocity | Reduces the cooldown on your Tiger's Fury ability by 3 sec. |

## New encounter names

34 new encounter IDs include 26 names absent from both reference encounter tables and eight familiar Sunken Temple names under new IDs. Counts below are client records, not a confirmed final encounter lineup.

### City of Dalaran (Map 2959)

Arcane Anomaly (3298), Fel Ancient (3299), Mana Devourer (3300), Mana Elemental (3301), Unstable Sentinel (3302), Shade of the Archmage (3303), Lyn the Ignored (3310), Atrexis the Grave Knight (3311), Mana Wraith (3312)

### Excavation Site: Wetlands (Map 2998)

Saltspine (3480), Shadetooth (3481), Highland Horror (3644), Relic Guardian (3482)

### Ruins of Lordaeron (Map 2999)

Witherfang (3353), The Abandoned (3357), The Butcher (3355), Rath'mael (3354), Lordaeron Captain (3408), Viktor the Vile (3411), Bjork (3412)

### Half-Pint Tavern (Map 3002)

Deathulus (3369), Crushfist Bloodbreaker (3371)

### The Hall of Thanes (Map 3065)

Faldrim Anvilmar (3493), Infurnus (3495), Plunder (3494), Durgen Dirgehammer (3496)

## Raids and limits

[Blizzard announced Hyjal Summit (20 players), Barrow Deeps (10 players) and nine dungeons](https://worldofwarcraft.blizzard.com/en-us/news/24303862/world-of-warcraft-forever-whats-next-panel-recap). Those announcements are tracked separately from client findings.

No newly added map has InstanceType=2 (raid) in this snapshot. Hyjal Crater (2995) has InstanceType=4 (arena); it must not be substituted for Hyjal Summit. No boss roster for Hyjal Summit or Barrow Deeps was established from the inspected tables.

Half-Pint Tavern (3002) and Manor Mistmantle (3109) are dungeon-type records, but are not established as announced dungeons. The former has two encounter records; the latter has none. They may represent quest spaces or unfinished content.

Creature.db2 is not a complete server NPC database. The inspected tables cannot verify world-boss spawns, drop tables, release readiness or hidden/encrypted/unavailable content. An absent record does not prove cancelled content.

The Retribution set’s 4-piece internal spell name says Undead, while the description says Demons. Both are retained in the viewer. Guardian in the Druid set labels means a bear-role label in these records, not evidence of a fourth talent tree.

## Reproduction

Source tables: ItemSet, ItemSetSpell, ItemSparse, ItemEffect, Map, MapDifficulty, DungeonEncounter, AreaTable, LFGDungeons and Creature. JournalInstance, JournalEncounter, JournalEncounterCreature, JournalEncounterItem and JournalEncounterSection were independently decoded and are empty.

[Extraction hashes and field comparison](content-audit.json) · [All findings and source IDs](content-data.json).

Uses the CASCLib / DBCD extraction method and source revisions documented in [the talent audit](audit.md). Map, AreaTable and ItemSparse anonymous export columns are mapped to the independently named DB2 layout in column order; mappings and schema hashes are recorded in the audit.

With the preserved source exports and decoded client files present, run `python scripts/build_content.py`. The builder asserts source equality, baseline classification, all 18 tier-set bonus thresholds, Classic tier references and encounter counts before writing the page.
