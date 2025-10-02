# VAPOR v3.0 - Installation Guide

## Quick Install (Recommended)

### Windows
1. Download `VAPOR_v3.0.zip` from [Releases](../../releases)
2. Extract to any folder
3. Run `VAPOR.exe`
4. Done! No Python needed.

### Linux
```bash
# Download and extract
wget https://github.com/wesellis/VAPOR/releases/download/v3.0/VAPOR_v3.0_Linux.tar.gz
tar -xzf VAPOR_v3.0_Linux.tar.gz
chmod +x VAPOR
./VAPOR
```

### macOS
```bash
# Download and extract
curl -L https://github.com/wesellis/VAPOR/releases/download/v3.0/VAPOR_v3.0_macOS.zip -o VAPOR.zip
unzip VAPOR.zip
chmod +x VAPOR.app/Contents/MacOS/VAPOR
open VAPOR.app
```

## First Run Setup

1. **Get API Keys** (free, takes 2 minutes):
   - Steam API: https://steamcommunity.com/dev/apikey
   - SteamGridDB: https://www.steamgriddb.com/profile/preferences/api

2. **Find Your Steam ID**:
   - Go to your Steam profile
   - The number in the URL is your Steam ID
   - Example: `steamcommunity.com/profiles/76561198000000000`

3. **Configure VAPOR**:
   - Paste your Steam API key
   - Paste your SteamGridDB key
   - Enter your Steam ID
   - Click "Save & Test"

4. **Process Your Library**:
   - Click "Load Games"
   - Click "Process All"
   - Wait ~30 seconds for 100 games

## Troubleshooting

### Windows Issues

**"VAPOR.exe won't start"**
- Install [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- Right-click → Run as Administrator

**"Windows Defender blocks it"**
- Click "More info" → "Run anyway"
- Or add exception in Windows Defender

### Common Issues

**"No games found"**
- Make sure your Steam profile is public
- Check Steam ID is correct (numbers only)

**"API key invalid"**
- Steam key: Must be from the account that owns the games
- SteamGridDB: Check for extra spaces when copying

**"Artwork not applying"**
- Restart Steam after processing
- Check Steam is installed in default location

**"Some games fail"**
- Normal for obscure games
- Click "Resume Failed" to retry
- Games not on SteamGridDB will fail

### Linux/macOS Issues

**"Permission denied"**
```bash
chmod +x VAPOR
```

**"Can't find Steam folder"**
- VAPOR looks in standard locations
- For custom installs, set STEAM_PATH environment variable

## Building from Source

If you want to build it yourself:

```bash
# Clone repo
git clone https://github.com/wesellis/VAPOR.git
cd VAPOR

# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build executable
python build_installer.py

# Output in dist/VAPOR.exe
```

## System Requirements

- **OS**: Windows 10+, Ubuntu 20.04+, macOS 10.14+
- **RAM**: 4GB minimum
- **Disk**: 100MB for app + cache
- **Internet**: Required for downloading artwork
- **Steam**: Must be installed

## What's Actually Improved in v3.0

1. **4x Faster** - Parallel processing
2. **Resume Support** - Continues after crashes
3. **Better Errors** - Clear messages about what failed
4. **Retry Failed** - One button to retry failures
5. **Single EXE** - No Python installation needed

## Support

- **Issues**: [GitHub Issues](../../issues)
- **Wiki**: [GitHub Wiki](../../wiki)
- **Logs**: Check `~/.vapor/vapor.log` for errors

---

That's it! VAPOR should now be processing your Steam library.