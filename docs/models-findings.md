# WoW Forever model gallery

Build **1.60.1.69876**, extracted from the public client CDN using the pinned build configuration in the existing audit.

[Open the interactive gallery](https://maf2414.github.io/wow-forever-talents/models.html).

- **125 sets** have appearance data, including all **18 new Tier 1 sets**, **60 PvP sets** and **47 other sets**.
- **116 sets** have standalone geometry. The other nine provide body texture sections.
- All **108 Tier 1 member IDs** resolve through ItemModifiedAppearance and ItemAppearance despite their missing ItemSparse metadata. All 18 tier sets provide a Human male helm and both shoulder models.
- **231 distinct textured GLB previews**, including **36 creature appearances**. Shared geometry/textures are deduplicated.
- The armor is shown as individual equipment pieces plus body texture sections. Full dressed characters, animation, particle effects and extra additive shader passes are not assembled.

## Bosses and creatures

DungeonEncounter has no model link in this build. JournalEncounterCreature and the other inspected journal tables are empty, and none of the 26 new encounter names match the small Creature.db2 cache. No boss name has been assigned to an unrelated appearance.

The creature selection contains model IDs absent from the SoD 1.15.9.69722 reference table and geometry FileDataIDs above 7,000,000, with a non-character CreatureDisplayInfo row supplying replacement textures. This is a bounded selection, not a census of every new creature or boss. Each preview uses its displayed DisplayID; other client variants may exist. Internal names are stripped in these files, so entries retain their client model IDs. Eight further selected records require unavailable assets and are omitted from the visible gallery.

## Data and reproduction

Armor: ItemSet → Item → ItemModifiedAppearance (default modifier) → ItemAppearance → ItemDisplayInfo → ModelFileData / ComponentModelFileData. Textures use ItemDisplayInfoModelMatRes, ItemDisplayInfoMaterialRes and TextureFileData. Nonzero replacement texture types come from the selected display; fixed textures come from the M2 TXID chunk. Geometry uses the first SFID skin, its vertex lookup, triangle indices and base material batches.

CreatureModelData + CreatureDisplayInfo supply creature geometry and skins. All 13 appearance tables were independently decoded with DBCD from CASC. [Table and asset hashes](models-audit.json) and [resolved appearance links](models-data.json) are published. The source assets remain outside the repository; browser previews contain converted geometry and textures only.

Run `python scripts/build_models.py inventory`, extract the resulting `model-asset-ids.json` with `ClientAudit --assets`, then run `dependencies`, extract again and run `build`. The inventory consumes the existing content dataset and decoded appearance tables. `node scripts/verify_models.cjs` validates every GLB with Khronos glTF Validator 2.0.0-dev.3.10 and checks tier coverage, texture references and item/display links.

M2/SKIN structure reference: [wow.export](https://github.com/Kruithne/wow.export/tree/c2fd7bde36a712be78a5da896c995b84fbfa2545), MIT license retained in `vendor/wow-export-LICENSE`. Viewer: Three.js 0.180.0, self-hosted with its MIT license. Game models and textures belong to Blizzard Entertainment.
