# Music Tools Suite

[![CI](https://github.com/your-org/music-tools/workflows/CI/badge.svg)](https://github.com/your-org/music-tools/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive suite of Python-based music management and processing tools, providing unified solutions for music library management, metadata tagging, and content discovery across multiple platforms.

## 📚 Documentation

- **[Installation & Setup](docs/getting-started/installation.md)**: Get up and running quickly.
- **[Feature Overview](docs/features/overview.md)**: Detailed breakdown of all tools.
- **[Library Management](docs/features/library-management.md)**: Guide to duplicate detection and library vetting.

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   cd packages/common && pip install -e ".[dev]"
   cd ../../apps/music-tools && pip install -r requirements.txt
   ```

2. **Run the App**:
   ```bash
   cd apps/music-tools
   python3 menu.py
   ```

## 📂 Project Structure

```
music-tools-suite/
├── apps/
│   └── music-tools/              # Main unified application
│       ├── menu.py               # Entry point
│       └── src/                  # Source code (Library, Scraper, Tagger)
├── packages/
│   └── common/                   # Shared library (Config, DB, UI)
└── docs/                         # Documentation
```

## 🛠️ Development

For development guidelines, please refer to the `docs/development/` directory (coming soon).

## License

This project is licensed under the MIT License.
