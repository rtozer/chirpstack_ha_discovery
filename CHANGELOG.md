# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Ongoing development

## [0.2.0] - 2025-07-24
### Added
- **Historic backfill functionality for InfluxDB:** The integration can now write historic sensor data (from device history or batch uploads) directly to InfluxDB, using the correct timestamp for each value.
- Backfill points are deduplicated and only written if they differ from the previous value in InfluxDB.
- Tag handling and deduplication logic improved for robust querying across all tag sets.

### Note
- Backfill only works with InfluxDB. Home Assistant does **not** allow historic writes to its internal database (SQLite/MariaDB); only the current state can be set in HA.

## [x.y.z] - YYYY-MM-DD
### Added
- Initial entry for new version.

### Changed
- 

### Fixed
- 

---

**Note:**
- When you update the `VERSION` file and push a new release, add a new section here for the version and a summary of changes.
- The GitHub Actions release workflow can be updated to use the latest entry from this file as the release description. 