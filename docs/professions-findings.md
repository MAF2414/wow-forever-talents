# Profession findings — September 17, 2026

Forever 1.60.1.69876. [Open the profession viewer](https://maf2414.github.io/wow-forever-talents/professions.html).

## Catalog

Counts below include recipes and enchantments with named spell records. Explicit Season of Discovery categories are excluded from the main counts. New means the spell ID is absent from both the Classic and SoD spell-name tables; new IDs can produce familiar items.

| Profession | Recipes | New IDs | Changed vs. Classic | Camping IDs |
|---|---:|---:|---:|---:|
| Alchemy | 182 | 71 | 48 | 3 |
| Blacksmithing | 447 | 203 | 207 | 3 |
| Enchanting | 222 | 63 | 114 | 3 |
| Engineering | 250 | 80 | 22 | 3 |
| Herbalism | 3 | 3 | 0 | 3 |
| Leatherworking | 524 | 283 | 205 | 3 |
| Mining | 18 | 5 | 0 | 3 |
| Skinning | 3 | 3 | 0 | 3 |
| Tailoring | 423 | 186 | 212 | 4 |
| Cooking | 125 | 44 | 9 | 5 |
| First Aid | 32 | 17 | 1 | 3 |
| Fishing | 3 | 3 | 0 | 3 |

## Reading the data

Recipe ingredients come from SpellReagents; results come from create-item effects. Tools and crafting stations use SpellTotems and SpellCastingRequirements. Recipe books are joined through ItemXItemEffect and ItemEffect trigger type 6. Book requirements are displayed separately from skill-up thresholds; the client ability minimum is not used as a trainer learning requirement.

The comparison covers recipe names, descriptions, ingredients, results, cast times, cooldowns, tools, stations and skill-up thresholds. It does not equate an unchanged recipe with unchanged item stats. Classic-only records can be inspected separately. Missing current item metadata is retained as an ID; a Classic name is explicitly labeled.

## Notable findings

First Aid has six healing potion recipes from Minor through Major, plus tourniquets, poultices and anti-venoms. All twelve professions have camping recipes. Blueprint item requirements include skill 140 for Tanning Rack and Repair Bot. Heavy Thorium smelting requires a Molten Foundry.

Ten familiar specialization spells remain linked to Blacksmithing, Leatherworking and Engineering. Jewelcrafting appears under a Test Profession with categories explicitly named PROTOTYPE; it is not counted among the twelve professions.

## Sources

[Profession data](professions-data.json) · [Extraction audit](professions-audit.json). The audit includes the independently decoded additional tables and links to the earlier spell, item and item-effect audits.
