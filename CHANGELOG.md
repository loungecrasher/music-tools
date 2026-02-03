# Changelog

All notable changes to the Music Tools Suite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive security audit and remediation
- Automated dependency vulnerability scanning setup
- Security module with path traversal prevention
- Cache file permission enforcement (0o600)
- Type hints across 65% of codebase

### Changed
- **BREAKING**: Fixed legacy tool paths - all legacy tools now in `legacy/` directory
- Updated test coverage documentation (from claimed 90%+ to actual ~35%)
- Improved error handling - replaced bare `except:` clauses with specific exceptions
- Enhanced logging with sanitization for sensitive data

### Fixed
- Fixed 11 bare except clauses (security/stability risk)
- Fixed cache file permissions vulnerability
- Fixed menu.py paths for legacy tools
- Corrected false test coverage claims in documentation

### Security
- Implemented secure file permissions (0o600/0o700)
- Added credential sanitization in logs
- Environment variable-based credential management
- Path traversal prevention in file operations

## [1.0.0] - 2025-11-15

### Added
- Monorepo structure with apps/ and packages/ organization
- Shared library `music_tools_common` with core functionality
- Security remediation (comprehensive security review completed)
- Rich terminal UI with themes and interactive menus
- Typer-based modern CLI interface

### Migrated
- Music Tools app to shared library architecture
- Configuration management to centralized system
- Database operations to shared package
- Authentication (Spotify/Deezer) to shared modules

### Documentation
- Complete README hierarchy
- Architecture Decision Records (ADRs)
- Security documentation (SECURITY.md)
- Development guides and quickstart
- API examples and migration guides

## [0.9.0] - Initial Release

### Added
- Spotify playlist management tools
- Deezer playlist availability checker
- Library comparison and duplicate removal
- EDM blog scraper for download links
- AI-powered country-of-origin music tagger
- Soundiz file processor
- CSV batch converter

---

## Version History

- **1.0.0** - Monorepo migration complete, production-ready shared library
- **0.9.0** - Initial standalone tools collection

For detailed information about specific changes, see the documentation in `docs/architecture/`.

## Migration Guides

### Upgrading from 0.9.x to 1.0.0

**Breaking Changes:**
1. **Import Paths**: All imports now use `music_tools_common`
   ```python
   # Old (0.9.x)
   from config import ConfigManager

   # New (1.0.0+)
   from music_tools_common.config import ConfigManager
   ```

2. **Configuration Location**: Configs moved to `~/.music_tools/`
   - Old: Multiple scattered config files
   - New: Centralized in user home directory

3. **Legacy Tools**: Moved to `apps/music-tools/legacy/`
   - Update any scripts that reference old paths

**Data Migration:**
- Database files automatically migrated on first run
- Configuration files: Use setup wizard or copy manually

For detailed migration instructions, see `packages/common/README.md`.

## Roadmap

### Q1 2025
- [ ] Increase test coverage to 60%
- [ ] Complete tag-editor migration
- [ ] Complete edm-scraper migration
- [ ] Add integration tests

### Q2 2025
- [ ] Achieve 80% test coverage
- [ ] Split Database class into repositories
- [ ] Add database abstraction layer
- [ ] Implement dependency injection framework

### Q3 2025
- [ ] API reference documentation
- [ ] Performance optimization
- [ ] Enhanced CLI framework
- [ ] Configuration system v2

---

**Maintained by**: Music Tools Team
**License**: MIT
**Status**: Production-ready (shared library), Migration in progress (apps)
