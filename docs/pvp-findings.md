# PvP findings — September 17, 2026

Forever 1.60.1.69876. [Open the PvP viewer](https://maf2414.github.io/wow-forever-talents/content.html#pvp).

## Honor and ranks

Honor Points (currency 1792) purchase PvP items and have a stored maximum of 15,000. Rank Points (3468) come from battlegrounds and tasks in Gadgetzan, and raise PvP rank. The two currencies have different purposes.

The PvP rank interface displays season progress, a weekly increasing cap and upcoming rewards. The cap curve runs through ranks 3, 5, 6, 7, 8, 9, 11, 12, 13 and 14. Its raw input/output pairs are included in the JSON; no calendar dates are assigned to these points.

| Rank | Alliance | Horde | Unlocks |
|---|---|---|---|
| 1 | Private | Scout | Faction Tabard |
| 2 | Corporal | Grunt | Insignia Trinket |
| 3 | Sergeant | Sergeant | Faction Cloak |
| 4 | Master Sergeant | Senior Sergeant | Faction Necklace |
| 5 | Sergeant Major | First Sergeant | Combat Potions |
| 6 | Knight | Stone Guard | Elite Faction Tabard |
| 7 | Knight-Lieutenant | Blood Guard | Battle Standard |
| 8 | Knight-Captain | Legionnaire | Elite Wrist Upgrade, Elite Waist Upgrade |
| 9 | Knight-Champion | Centurion | Elite Boot Upgrade |
| 10 | Lieutenant Commander | Champion | Elite Glove Upgrade |
| 11 | Commander | Lieutenant General | Black War Mounts |
| 12 | Marshal | General | Elite Leg Upgrade, Elite Shoulder Upgrade |
| 13 | Field Marshal | Warlord | Elite Chest Upgrade, Elite Helmet Upgrade |
| 14 | Grand Marshal | High Warlord | Weapon Arsenal |

Rewards are purchased in the Champion’s Hall in Stormwind or the Hall of Legends in Orgrimmar.

## Darkspear Islands

15 players per side. Brackets: 30–39, 40–49, 50–59 and 60. Capture and hold bases, then carry the Darkspear Flag to a controlled point for Victory Points. The map objective lists 1,500 resources. Scoreboard columns cover flag captures, bases assaulted and bases defended.

Horde reputation: Darkspear Raiders (2798). Alliance reputation: Theramore Expeditionary Force (2799). Each has 22 associated item records. Friendly unlocks trinkets; Honored includes rings and neck items; Exalted includes epic gloves, shoulders and a tabard. Level 60 epics in this group have item level 65.

## Queues and additional entries

Random Battleground links to Warsong Gulch, Arathi Basin and Darkspear Islands. A separate Random Epic Battleground entry has no linked map rows. Battle for Blackrock is already present in the SoD reference.

Battle for Gilneas, Hyjal Crater and Mak’gora Arena have additional queue records. Both arena entries link to map 2995. They are shown as additional client entries, not announced modes. No rated-arena feature is inferred from the RatedPlayers field.

## Armor and purchases

26 new PvP set IDs plus 34 changed Classic PvP sets cover all nine classes. The viewer provides class/faction filters and every set bonus. There are also 23 Honor-based extended-cost rows; the JSON retains these without assigning them to vendor items.

## Sources

[PvP table audit](pvp-audit.json) · [All PvP findings](pvp-data.json). Bonus spells and item metadata use the existing client extraction. The new PvP rank Lua/XML and API documentation were also read directly from the client archives.
