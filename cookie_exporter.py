#!/usr/bin/env python3
"""
cookie_exporter.py

A local script that reads cookies from a Chrome 'Cookies' database file
and exports them in Netscape format. You can specify:

- Chrome profile path
- Domain(s)
- Output path

Optionally, use a YAML config file with the --use-config flag.

Usage Examples:

1) Direct CLI arguments:

   python cookie_exporter.py \
       --chrome-profile "/path/to/Default/Cookies" \
       --domain "youtube.com" \
       --domain "instagram.com" \
       --output "/path/to/output/cookies.txt"

2) Use config file (defaults to ~/.cookie_exporter/config.yaml):

   python cookie_exporter.py --use-config

Author: [Your Name]
License: MIT (or your choice)
"""
import os
import sys
import sqlite3
import shutil
import tempfile
import argparse

# If needed for encrypted cookies on Windows/macOS:
# from Cryptodome.Cipher import AES
# import keyring  # for macOS Keychain or Windows DPAPI access

# For reading YAML config if desired
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

def parse_args():
    parser = argparse.ArgumentParser(
        description="Export Chrome cookies in Netscape format."
    )
    parser.add_argument(
        "--chrome-profile",
        help="Path to the Chrome 'Cookies' SQLite database file.",
        type=str
    )
    parser.add_argument(
        "--domain",
        help="Domain(s) to filter for. Can be repeated.",
        action="append"
    )
    parser.add_argument(
        "--output",
        help="Output file path for the exported Netscape file.",
        type=str
    )
    parser.add_argument(
        "--use-config",
        help="Load parameters (chrome_profile, domains, output_path) from config file.",
        action="store_true"
    )
    return parser.parse_args()

def load_config_file():
    """
    Loads YAML config from a predetermined location, e.g.:
        ~/.cookie_exporter/config.yaml
    
    Returns a dict with at least:
      {
        "chrome_profile": "...",
        "domains": [...],
        "output_path": "..."
      }
    """
    default_path = os.path.expanduser("~/.cookie_exporter/config.yaml")
    if not os.path.isfile(default_path):
        print(f"[ERROR] Config file not found at {default_path}", file=sys.stderr)
        sys.exit(1)
    
    if not HAS_YAML:
        print("[ERROR] PyYAML is not installed. Install it or remove --use-config", file=sys.stderr)
        sys.exit(1)
    
    with open(default_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data

def copy_sqlite_db(src_path):
    """
    Copy the Chrome Cookies DB to a temporary file
    so we can read it without Chrome locking it.
    Returns the path to the temporary copy.
    """
    tmp_file = os.path.join(tempfile.gettempdir(), "chrome_cookies_export_temp.db")
    shutil.copy2(src_path, tmp_file)
    return tmp_file

def get_chrome_cookies(chrome_db_path, filter_domains=None):
    """
    Retrieves cookies from the specified Chrome 'Cookies' database path.
    filter_domains: list of domains (strings) to filter.
        If None or empty, returns all cookies.
    Returns a list of cookie dicts of the form:
        {
          "domain": str,
          "name": str,
          "value": str,
          "path": str,
          "secure": bool,
          "expires_utc": int  (Chrome's internal timestamp)
        }
    """
    tmp_file = copy_sqlite_db(chrome_db_path)

    conn = sqlite3.connect(tmp_file)
    cursor = conn.cursor()

    # Chrome's cookies table typically has columns like:
    # host_key, name, value, path, expires_utc, is_secure, ...
    # but this might vary by Chrome version.
    if filter_domains:
        results = []
        for dom in filter_domains:
            # Use LIKE matching for domain
            # (some cookies have preceding '.' in the host_key, etc.)
            like_pattern = f"%{dom}%"
            cursor.execute("""
                SELECT host_key, name, value, path, expires_utc, is_secure
                FROM cookies
                WHERE host_key LIKE ?
            """, (like_pattern,))
            results.extend(cursor.fetchall())
    else:
        cursor.execute("SELECT host_key, name, value, path, expires_utc, is_secure FROM cookies")
        results = cursor.fetchall()

    cookies = []
    for host_key, name, value, path, expires_utc, is_secure in results:
        cookies.append({
            "domain": host_key,
            "name": name,
            "value": value,
            "path": path,
            "secure": bool(is_secure),
            "expires_utc": expires_utc
        })

    conn.close()
    # Cleanup temp DB
    if os.path.exists(tmp_file):
        os.remove(tmp_file)

    return cookies

def convert_chrome_timestamp_to_unix(chrome_ts):
    """
    Chrome's 'expires_utc' is the number of microseconds since 1601-01-01.
    We convert to Unix epoch: number of seconds since 1970-01-01.

    If expires_utc is 0 or None, treat it as session cookie => set expiry to 0 or some default.
    """
    if not chrome_ts:
        return 0
    # 11644473600 = difference in seconds between 1970 and 1601
    return int(chrome_ts / 1000000 - 11644473600)

def to_netscape(cookies):
    """
    Convert a list of cookie dicts to Netscape HTTP Cookie File format.

    Example format line:
    domain <tab>  TRUE/FALSE <tab> path <tab> TRUE/FALSE <tab> expiry-epoch <tab> name <tab> value

    domain: The domain that set the cookie.
    Include leading '.' if cookie is valid for subdomains.
    """
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        domain = c["domain"]
        # If the cookie domain starts with '.', the second domain field is "TRUE"
        # indicating it's valid for subdomains. Otherwise, "FALSE".
        # But it can get tricky—some prefer to always set "FALSE" if it's not an explicitly
        # domain cookie. We'll do a naive approach:
        domain_cookie_flag = "TRUE" if domain.startswith('.') else "FALSE"

        path = c["path"]
        secure_flag = "TRUE" if c["secure"] else "FALSE"
        expiry_epoch = convert_chrome_timestamp_to_unix(c["expires_utc"])
        name = c["name"]
        value = c["value"]

        line = f"{domain}\t{domain_cookie_flag}\t{path}\t{secure_flag}\t{expiry_epoch}\t{name}\t{value}"
        lines.append(line)

    return "\n".join(lines)

def main():
    args = parse_args()

    # If --use-config is specified, load from config
    if args.use_config:
        config_data = load_config_file()
        chrome_profile = config_data.get("chrome_profile")
        domain_list = config_data.get("domains", [])
        output_path = config_data.get("output_path", "cookies.txt")
    else:
        # Use CLI arguments
        chrome_profile = args.chrome_profile
        domain_list = args.domain or []
        output_path = args.output

    if not chrome_profile:
        print("[ERROR] Chrome profile path is required (either via CLI or config).", file=sys.stderr)
        sys.exit(1)
    if not output_path:
        print("[ERROR] Output file path is required (either via CLI or config).", file=sys.stderr)
        sys.exit(1)

    # Retrieve cookies
    cookies = get_chrome_cookies(chrome_profile, filter_domains=domain_list)
    # Convert to Netscape
    netscape_txt = to_netscape(cookies)

    # Write to output file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(netscape_txt)
        print(f"Cookies exported successfully to {output_path}")
    except Exception as e:
        print(f"[ERROR] Failed to write cookies to {output_path}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
    