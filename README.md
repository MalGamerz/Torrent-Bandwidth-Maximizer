# Torrent Bandwidth Maximizer

A Python utility designed to maximize your bandwidth utilization by repeatedly downloading torrents in a controlled manner.

## Description

This tool helps maximize your internet connection's bandwidth by continuously downloading the same torrent file multiple times. It's useful for:

- Testing the maximum throughput of your internet connection
- Utilizing unused bandwidth during off-peak hours
- Demonstrating network capacity to ISPs
- Benchmarking download speeds over extended periods

The tool leverages qBittorrent's API to manage downloads efficiently, with built-in error handling and cleanup processes.

## Prerequisites

- Python 3.6+
- qBittorrent client installed and running with WebUI enabled
- Administrative privileges (for process management)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/torrent-bandwidth-maximizer.git
   cd torrent-bandwidth-maximizer
   ```

2. Install required dependencies:
   ```bash
   pip install qbittorrent-api requests tqdm psutil
   ```

## Configuration

Before running the tool, modify the following parameters in the script according to your environment:

```python
# Configuration
QB_HOST = "http://localhost:8080"  # qBittorrent WebUI address
QB_USER = "admin"                  # qBittorrent WebUI username
QB_PASS = "password"               # qBittorrent WebUI password
SAVE_PATH = r"C:\tmp\ubuntu_torrents"  # Directory for temporary downloads
MAX_ITERATIONS = 10000             # Number of download iterations to perform
MAX_WORKERS = 1                    # Maximum concurrent downloads
MAX_ACTIVE_TORRENTS = 1            # Maximum active torrents at once
LOGGING_INTERVAL = 5               # Seconds between progress logs
TORRENT_URL = "https://releases.ubuntu.com/24.04/ubuntu-24.04.2-desktop-amd64.iso.torrent"  # Torrent to download
```

You can adjust these values to:
- Increase `MAX_WORKERS` and `MAX_ACTIVE_TORRENTS` to utilize more bandwidth
- Change the `TORRENT_URL` to any legal torrent you prefer to download
- Modify `SAVE_PATH` to specify where the temporary files will be stored

## Usage

1. Configure qBittorrent:
   - Enable WebUI in qBittorrent preferences
   - Set up username and password for WebUI access
   - Ensure qBittorrent is running

2. Run the bandwidth maximizer:
   ```bash
   python bandwidth_maximizer.py
   ```

3. Monitor bandwidth utilization:
   - Real-time progress and download speed are shown in the console
   - Detailed logs are saved to `ubuntu_stress_test.log` file
   - Check your network monitor to observe bandwidth consumption

4. Stop the downloads:
   - Press Ctrl+C to gracefully stop the process
   - The script will automatically clean up any in-progress downloads

## How It Works

1. **Setup Phase**:
   - Creates necessary directories for temporary files
   - Validates the torrent URL
   - Cleans up any existing torrents from previous runs

2. **Download Process**:
   - Creates a thread pool to manage concurrent downloads
   - For each iteration:
     - Creates a unique temporary directory
     - Adds the torrent to qBittorrent with a unique category
     - Downloads the torrent file completely
     - Upon completion, deletes the torrent and cleans up files
     - Starts the next download cycle
     - Logs all actions and download speeds

3. **Resource Management**:
   - Automatically cleans up completed downloads to save disk space
   - Implements retry logic for network issues
   - Handles interruptions gracefully with proper cleanup

## Performance Tips

- To maximize bandwidth usage:
  - Increase the `MAX_WORKERS` and `MAX_ACTIVE_TORRENTS` values
  - Use well-seeded torrents with many peers
  - Run the tool during times when your network is otherwise idle
  - Consider using a VPN that doesn't throttle torrent traffic
  - Adjust qBittorrent's connection settings for optimal performance

## Logging

The tool provides detailed logging at multiple levels:

- Console output shows real-time download speed and progress
- Comprehensive logs are written to `ubuntu_stress_test.log`
- Debug information including connections and errors is recorded

## Ethical Usage Note

This tool is intended for legitimate bandwidth utilization and testing purposes only. Please:
- Only download legal content (like Linux distributions)
- Be mindful of data caps on your internet plan
- Consider other network users on shared connections
- Comply with your ISP's terms of service

## License

MIT License

Copyright (c) 2025 MalGamerzs

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
