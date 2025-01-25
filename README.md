# Cookie Exporter

A local Python script that can extract cookies from a specified Google Chrome profile and export them in Netscape cookie format.

## Features

- Extract cookies by domain from a user-provided Chrome profile path.
- Outputs to a single `.txt` file in Netscape HTTP Cookie File format.
- Optional configuration file usage for easy repeated tasks.

## Prerequisites

- Python 3.7+ (preferably).
- Google Chrome installed (tested paths).
- (Optional) If Chrome stores cookies encrypted, you may need additional OS-specific libraries or the [PyCryptodome](https://pypi.org/project/pycryptodomex/) package to handle decryption.

## Installation

1. Clone this repository or download the files.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt



## Usage

### 1. Direct CLI arguments

```
python cookie_exporter.py \
    --chrome-profile "/path/to/Default/Cookies" \
    --domain "youtube.com" \
    --domain "instagram.com" \
    --output "/path/to/output/cookies.txt"
```

	•	–chrome-profile: Path to the Chrome “Cookies” SQLite DB.
	•	–domain: One or more domains you want to filter for.
	•	–output: Output file path for the exported Netscape-format cookies.

### 2. Using a config file

If you have a YAML config file (e.g., ~/.cookie_exporter/config.yaml) with content like:

```
chrome_profile: "/path/to/Default/Cookies"
domains:
  - "youtube.com"
  - "instagram.com"
output_path: "/path/to/output/cookies.txt"
```
Then run:

```
python cookie_exporter.py --use-config
```

The script will automatically read from your config file and use those settings.

(You can also pass a custom config path if you extend the script with a --config <path> argument.)
