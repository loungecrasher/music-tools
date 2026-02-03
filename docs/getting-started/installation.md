# Installation & Setup

## Prerequisites
- **Python 3.8** or higher
- **pip** (Python package installer)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/music-tools.git
   cd music-tools
   ```

2. **Install the shared library** (Required):
   ```bash
   cd packages/common
   pip install -e ".[dev]"
   ```

3. **Install application dependencies**:
   ```bash
   cd ../../apps/music-tools
   pip install -r requirements.txt
   ```

## Configuration

The first time you run the application, you may need to configure API credentials for services like Spotify or Deezer.

### Spotify Setup
1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
2. Create a new application.
3. Set the Redirect URI to `http://localhost:8888/callback`.
4. Copy the **Client ID** and **Client Secret**.
5. Run the app and use the **Configuration** menu to enter these details.

### Deezer Setup
1. Run the app and use the **Configuration** menu.
2. Enter your Deezer email/credentials when prompted (or via browser auth).

## Running the Application

To launch the main unified menu:

```bash
cd apps/music-tools
python3 menu.py
```
