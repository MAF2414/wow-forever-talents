# WoW Forever vs. Classic — Talents & Class Spells

An interactive, English-language viewer for all nine classes, with talent trees
and a side-by-side comparison against Classic Era.

**[Open the website](https://maf2414.github.io/wow-forever-talents/)**

## Features

- Switch between Forever and Classic talent trees for all 27 specializations.
- Inspect every talent rank, description and prerequisite.
- Enable **Level 60 planner** to allocate 51 points, with tier and prerequisite
  checks, safe refunds and separate saved builds for each class and version.
- See new, removed and changed talents, including highlighted text differences.
- Compare class spell ranks, costs, range, cast time, cooldowns and effect values.
- Search by talent name, spell name or spell ID.
- Optionally include passives, talent spells and seasonal or extra client data.
- Explore [sets, PvP, bosses and instances](https://maf2414.github.io/wow-forever-talents/content.html):
  51 new set IDs, 18 Tier 1 class/role sets with all bonuses, 80 changed Classic
  sets, and new map and encounter records with source IDs.
- Browse [PvP ranks and rewards](https://maf2414.github.io/wow-forever-talents/content.html#pvp):
  all 14 rank unlocks, Honor and Rank Points, Darkspear Islands objectives and
  brackets, 44 reputation item variants, and 60 new or updated PvP armor sets
  with class/faction filters and Classic bonus comparisons.
- Open `docs/index.html` directly for offline use: all data and icons are embedded.

## Data and scope

- **Forever:** 1.60.1.69876, snapshot dated September 16, 2026.
- **Classic baseline:** Era 1.14.4.51395, before Season of Discovery.
- **Talents:** 468 regular Forever nodes, 3 separately marked nodes outside the
  normal grid, and 432 Classic talents.
- **Spells:** 484 regular active spell groups, with additional passive, talent
  and seasonal records available through filters.

**[Client-file audit](docs/audit.md):** 42 Forever tables (243,982 records) were
independently decoded from Blizzard’s CDN and matched against the exports. The
audit also corrected duration formatting, explicit damage bounds and prerequisite
handling.

The source tables are public [Wago.Tools DB2 exports](https://wago.tools/builds).
The Forever SkillLineAbility layout is interpreted using
[WoWDBDefs](https://github.com/wowdev/WoWDBDefs/blob/master/definitions/SkillLineAbility.dbd).
Spell names, descriptions and icons are Blizzard game data and artwork.
This project is not affiliated with Blizzard Entertainment.

This is a **client-data comparison**, not a guarantee of in-game availability.
“Removed” means absent from the regular Forever talent tree. Data from
Era/SoD 1.15.9.69722 help identify inherited seasonal records; those records are
shown separately rather than counted as new Forever abilities.

Damage and healing use base values without character simulation. General damage
amounts and numeric effect comparisons use means; explicit minimum/maximum
expressions retain their bounds. Unresolved dynamic expressions remain
visible. “Unchanged” applies to the compared fields, not every possible server
rule. Triggered subspells, equipment, server hotfixes and additional conditions
are not fully simulated. Spells are matched by ID to preserve renames; different
IDs remain separate variants.

## Hosting

GitHub Pages publishes the **`/docs` folder on `main`**. The `.nojekyll` file
keeps this a plain static site. No backend, account system or API keys are needed.
Pushing an updated `docs/index.html` publishes the next version automatically.

## Local editing

The templates live in `site/`; the data builders and integrity checks live in
`scripts/`. Raw exports, downloaded archives and local research files are kept
under the ignored `evidence/` and `sources/` directories, and are not part of the
public repository.

Rebuilding requires Python 3, the cached DB2 exports and icon files under
`evidence/2026-09-16/`. `scripts/fetch_tables.ps1` downloads public tables by build
and folder. Once the source data are present:

```powershell
python scripts/build_comparison.py
python scripts/fetch_icons.py
python scripts/build_comparison.py
python scripts/verify_data.py
node --check evidence/2026-09-16/browser-script.js
node scripts/verify_planner.cjs
python scripts/build_content.py
```

The builder writes identical standalone pages to `dist/index.html` for local use
and `docs/index.html` for GitHub Pages. It also creates `dist/talents.json` for
further analysis; the HTML does not fetch that file.

The content research builder additionally requires the `content-forever`,
`content-classic`, `content-sod` exports and independently decoded
`audit/content-db2` files. It verifies every exported field against the decoded
client before generating `content.html`, its JSON data and the
[content findings report](docs/content-findings.md). All five journal tables are
empty in this build. Official raid announcements are listed separately from
the partial client evidence; no raid loot sources are inferred from set names.

PvP research additionally uses `pvp-forever`, `pvp-classic`, `pvp-sod` and
`audit/pvp-db2`. The build checks 17 nonempty PvP tables against the exports
and reads the rank interface directly from the client. It also generates the
[PvP findings](docs/pvp-findings.md), [data](docs/pvp-data.json) and
[source audit](docs/pvp-audit.json).

To preview locally:

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:8765/`.
