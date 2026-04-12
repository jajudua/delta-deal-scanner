#!/usr/bin/env python3
"""
Delta ATL International Flight Deal & Mistake Fare Scanner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scans 60 Delta nonstop international destinations from ATL
Region-based price thresholds for realistic deal detection
Runs ONCE WEEKLY via GitHub Actions ($25/mo SerpAPI Starter = 1,000 searches)
~186 API calls per weekly run (62 destinations x 3 date checks)
Searches ROUNDTRIP fares (7-day trips)
Outputs:
  1. Email alert with visual deal cards via Gmail SMTP
  2. HTML dashboard file (dashboard.html) for GitHub Pages or local viewing
  3. JSON data file (scan_results.json) for history tracking
"""

import os
import json
import requests
import sys
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── CREDENTIALS ──────────────────────────────────────────────────────────────
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")

if not SERPAPI_KEY:
    print("ERROR: SERPAPI_KEY not set")
    sys.exit(1)

ORIGIN = "ATL"

# ── REGION-BASED PRICE THRESHOLDS (roundtrip Main Cabin) ────────────────────
THRESHOLDS = {
    "caribbean":       {"deal": 350, "mistake": 200, "trip_days": 7},
    "mexico":          {"deal": 300, "mistake": 180, "trip_days": 7},
    "central_america": {"deal": 350, "mistake": 200, "trip_days": 7},
    "south_america":   {"deal": 550, "mistake": 350, "trip_days": 10},
    "canada":          {"deal": 250, "mistake": 130, "trip_days": 5},
    "europe":          {"deal": 650, "mistake": 400, "trip_days": 10},
    "africa":          {"deal": 800, "mistake": 500, "trip_days": 12},
    "middle_east":     {"deal": 800, "mistake": 500, "trip_days": 10},
    "asia":            {"deal": 800, "mistake": 500, "trip_days": 12},
}

# ── DELTA NONSTOP INTERNATIONAL DESTINATIONS FROM ATL ───────────────────────
DESTINATIONS = {
    # Caribbean (17)
    "SJU": {"name": "San Juan, Puerto Rico",          "region": "caribbean",      "flag": "\U0001f1f5\U0001f1f7"},
    "PLS": {"name": "Providenciales, Turks & Caicos", "region": "caribbean",      "flag": "\U0001f1f9\U0001f1e8"},
    "AUA": {"name": "Oranjestad, Aruba",              "region": "caribbean",      "flag": "\U0001f1e6\U0001f1fc"},
    "GCM": {"name": "Grand Cayman",                   "region": "caribbean",      "flag": "\U0001f1f0\U0001f1fe"},
    "MBJ": {"name": "Montego Bay, Jamaica",           "region": "caribbean",      "flag": "\U0001f1ef\U0001f1f2"},
    "KIN": {"name": "Kingston, Jamaica",              "region": "caribbean",      "flag": "\U0001f1ef\U0001f1f2"},
    "PUJ": {"name": "Punta Cana, DR",                 "region": "caribbean",      "flag": "\U0001f1e9\U0001f1f4"},
    "SDQ": {"name": "Santo Domingo, DR",              "region": "caribbean",      "flag": "\U0001f1e9\U0001f1f4"},
    "NAS": {"name": "Nassau, Bahamas",                "region": "caribbean",      "flag": "\U0001f1e7\U0001f1f8"},
    "UVF": {"name": "Vieux Fort, Saint Lucia",        "region": "caribbean",      "flag": "\U0001f1f1\U0001f1e8"},
    "GND": {"name": "St. George's, Grenada",          "region": "caribbean",      "flag": "\U0001f1ec\U0001f1e9"},
    "SVD": {"name": "St. Vincent & Grenadines",       "region": "caribbean",      "flag": "\U0001f1fb\U0001f1e8"},
    "BGI": {"name": "Bridgetown, Barbados",           "region": "caribbean",      "flag": "\U0001f1e7\U0001f1e7"},
    "SXM": {"name": "Philipsburg, St. Maarten",       "region": "caribbean",      "flag": "\U0001f1f8\U0001f1fd"},
    "ANU": {"name": "St. John's, Antigua",            "region": "caribbean",      "flag": "\U0001f1e6\U0001f1ec"},
    "SKB": {"name": "Basseterre, St. Kitts",          "region": "caribbean",      "flag": "\U0001f1f0\U0001f1f3"},
    "BDA": {"name": "Bermuda",                        "region": "caribbean",      "flag": "\U0001f1e7\U0001f1f2"},
    # Mexico (7)
    "CUN": {"name": "Cancun",                         "region": "mexico",         "flag": "\U0001f1f2\U0001f1fd"},
    "PVR": {"name": "Puerto Vallarta",                "region": "mexico",         "flag": "\U0001f1f2\U0001f1fd"},
    "SJD": {"name": "Los Cabos",                      "region": "mexico",         "flag": "\U0001f1f2\U0001f1fd"},
    "MEX": {"name": "Mexico City",                    "region": "mexico",         "flag": "\U0001f1f2\U0001f1fd"},
    "GDL": {"name": "Guadalajara",                    "region": "mexico",         "flag": "\U0001f1f2\U0001f1fd"},
    "MTY": {"name": "Monterrey",                      "region": "mexico",         "flag": "\U0001f1f2\U0001f1fd"},
    "MZT": {"name": "Mazatlan",                       "region": "mexico",         "flag": "\U0001f1f2\U0001f1fd"},
    # Central America (5)
    "SJO": {"name": "San Jose, Costa Rica",           "region": "central_america","flag": "\U0001f1e8\U0001f1f7"},
    "PTY": {"name": "Panama City, Panama",            "region": "central_america","flag": "\U0001f1f5\U0001f1e6"},
    "BZE": {"name": "Belize City, Belize",            "region": "central_america","flag": "\U0001f1e7\U0001f1ff"},
    "GUA": {"name": "Guatemala City",                 "region": "central_america","flag": "\U0001f1ec\U0001f1f9"},
    "SAL": {"name": "San Salvador",                   "region": "central_america","flag": "\U0001f1f8\U0001f1fb"},
    # South America (7)
    "BOG": {"name": "Bogota, Colombia",               "region": "south_america",  "flag": "\U0001f1e8\U0001f1f4"},
    "CTG": {"name": "Cartagena, Colombia",            "region": "south_america",  "flag": "\U0001f1e8\U0001f1f4"},
    "LIM": {"name": "Lima, Peru",                     "region": "south_america",  "flag": "\U0001f1f5\U0001f1ea"},
    "SCL": {"name": "Santiago, Chile",                "region": "south_america",  "flag": "\U0001f1e8\U0001f1f1"},
    "GRU": {"name": "Sao Paulo, Brazil",              "region": "south_america",  "flag": "\U0001f1e7\U0001f1f7"},
    "GIG": {"name": "Rio de Janeiro, Brazil",         "region": "south_america",  "flag": "\U0001f1e7\U0001f1f7"},
    "EZE": {"name": "Buenos Aires, Argentina",        "region": "south_america",  "flag": "\U0001f1e6\U0001f1f7"},
    # Canada (6)
    "YYZ": {"name": "Toronto",                        "region": "canada",         "flag": "\U0001f1e8\U0001f1e6"},
    "YUL": {"name": "Montreal",                       "region": "canada",         "flag": "\U0001f1e8\U0001f1e6"},
    "YVR": {"name": "Vancouver",                      "region": "canada",         "flag": "\U0001f1e8\U0001f1e6"},
    "YYC": {"name": "Calgary",                        "region": "canada",         "flag": "\U0001f1e8\U0001f1e6"},
    "YOW": {"name": "Ottawa",                         "region": "canada",         "flag": "\U0001f1e8\U0001f1e6"},
    "YHZ": {"name": "Halifax",                        "region": "canada",         "flag": "\U0001f1e8\U0001f1e6"},
    # Europe (12)
    "LHR": {"name": "London Heathrow",                "region": "europe",         "flag": "\U0001f1ec\U0001f1e7"},
    "CDG": {"name": "Paris CDG",                      "region": "europe",         "flag": "\U0001f1eb\U0001f1f7"},
    "AMS": {"name": "Amsterdam",                      "region": "europe",         "flag": "\U0001f1f3\U0001f1f1"},
    "FRA": {"name": "Frankfurt",                      "region": "europe",         "flag": "\U0001f1e9\U0001f1ea"},
    "MUC": {"name": "Munich",                         "region": "europe",         "flag": "\U0001f1e9\U0001f1ea"},
    "FCO": {"name": "Rome",                           "region": "europe",         "flag": "\U0001f1ee\U0001f1f9"},
    "MAD": {"name": "Madrid",                         "region": "europe",         "flag": "\U0001f1ea\U0001f1f8"},
    "BCN": {"name": "Barcelona",                      "region": "europe",         "flag": "\U0001f1ea\U0001f1f8"},
    "ATH": {"name": "Athens",                         "region": "europe",         "flag": "\U0001f1ec\U0001f1f7"},
    "DUB": {"name": "Dublin",                         "region": "europe",         "flag": "\U0001f1ee\U0001f1ea"},
    "ZRH": {"name": "Zurich",                         "region": "europe",         "flag": "\U0001f1e8\U0001f1ed"},
    "BRU": {"name": "Brussels",                       "region": "europe",         "flag": "\U0001f1e7\U0001f1ea"},
    # Africa (3)
    "JNB": {"name": "Johannesburg",                   "region": "africa",         "flag": "\U0001f1ff\U0001f1e6"},
    "RAK": {"name": "Marrakech",                      "region": "africa",         "flag": "\U0001f1f2\U0001f1e6"},
    "ACC": {"name": "Accra, Ghana",                   "region": "africa",         "flag": "\U0001f1ec\U0001f1ed"},
    # Middle East (2)
    "TLV": {"name": "Tel Aviv",                       "region": "middle_east",    "flag": "\U0001f1ee\U0001f1f1"},
    "RUH": {"name": "Riyadh",                         "region": "middle_east",    "flag": "\U0001f1f8\U0001f1e6"},
    # Asia (1)
    "HND": {"name": "Tokyo Haneda",                   "region": "asia",           "flag": "\U0001f1ef\U0001f1f5"},
}

SENT_ALERTS_FILE = "/tmp/delta_deals.json"
SCAN_RESULTS_FILE = "scan_results.json"
DASHBOARD_FILE = "dashboard.html"


# ── HELPERS ──────────────────────────────────────────────────────────────────

def load_sent_alerts():
    if os.path.exists(SENT_ALERTS_FILE):
        try:
            with open(SENT_ALERTS_FILE, 'r') as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_sent_alerts(alerts):
    with open(SENT_ALERTS_FILE, 'w') as f:
        json.dump(list(alerts), f)

def load_scan_history():
    if os.path.exists(SCAN_RESULTS_FILE):
        try:
            with open(SCAN_RESULTS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {"scans": []}
    return {"scans": []}

def save_scan_history(history):
    with open(SCAN_RESULTS_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def search_flights(origin, destination, departure_date, return_date):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": departure_date,
        "return_date": return_date,
        "type": "1",  # 1 = Round trip (SerpAPI default)
        "api_key": SERPAPI_KEY,
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  ERR {origin}-{destination}: {str(e)[:50]}", flush=True)
        return None

def is_nonstop_delta(flight):
    """Check if a flight result is nonstop Delta.
    SerpAPI structure: each item in best_flights/other_flights has a 'flights' array
    of segments. Nonstop = exactly 1 segment. Delta = airline name contains 'Delta'.
    """
    try:
        segments = flight.get("flights", [])
        # Nonstop means exactly 1 segment in the outbound
        if len(segments) != 1:
            return False
        # Check airline on the segment
        airline = segments[0].get("airline", "")
        if "Delta" not in airline:
            return False
        return True
    except Exception:
        return False

def classify_deal(price, region):
    t = THRESHOLDS.get(region, {"deal": 500, "mistake": 250})
    if price < t["mistake"]:
        return "MISTAKE FARE"
    elif price < t["deal"]:
        return "GREAT DEAL"
    return None

def parse_flights(data, dest_code, dest_info, departure_date, return_date):
    deals = []
    if not data:
        return deals
    region = dest_info["region"]
    threshold = THRESHOLDS[region]["deal"]
    for flight_group in ["best_flights", "other_flights"]:
        for flight in data.get(flight_group, []):
            try:
                if not is_nonstop_delta(flight):
                    continue
                price = flight.get("price")
                if not price or price >= threshold:
                    continue
                deal_type = classify_deal(price, region)
                if not deal_type:
                    continue
                deals.append({
                    "origin": "ATL",
                    "destination": dest_code,
                    "destination_name": dest_info["name"],
                    "region": region,
                    "flag": dest_info.get("flag", ""),
                    "price": price,
                    "type": deal_type,
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "found_at": datetime.now().isoformat(),
                })
            except Exception:
                continue
    return deals


# ── EMAIL WITH DEAL CARDS ────────────────────────────────────────────────────

def _email_card(deal):
    is_mistake = "MISTAKE" in deal["type"]
    border = "#d32f2f" if is_mistake else "#2e7d32"
    bg = "#fff5f5" if is_mistake else "#f1f8e9"
    badge_bg = "#d32f2f" if is_mistake else "#2e7d32"
    badge_txt = "MISTAKE FARE - BOOK NOW" if is_mistake else "GREAT DEAL"
    flag = deal.get("flag", "")
    region = deal["region"].replace("_", " ").title()
    delta_url = (
        f"https://www.delta.com/flight-search/search?cacheKeySuffix=a"
        f"&fromCity=ATL&toCity={deal['destination']}"
        f"&departureDate={deal['departure_date']}"
        f"&returnDate={deal.get('return_date', '')}"
        f"&tripType=ROUND_TRIP&paxCount=1&cabinType=MAIN"
    )
    return f"""
    <div style="border:2px solid {border};border-radius:12px;margin-bottom:16px;
                overflow:hidden;background:{bg};font-family:Arial,sans-serif;">
      <div style="background:{badge_bg};color:#fff;padding:6px 16px;
                  font-size:11px;font-weight:bold;letter-spacing:1px;">
        {badge_txt}
      </div>
      <div style="padding:16px;">
        <table width="100%" cellpadding="0" cellspacing="0"><tr>
          <td style="vertical-align:top;">
            <div style="font-size:12px;color:#888;">{flag} {region}</div>
            <div style="font-size:22px;font-weight:bold;color:#1a1a1a;">ATL &harr; {deal["destination"]}</div>
            <div style="font-size:14px;color:#444;margin-top:2px;">{deal["destination_name"]}</div>
            <div style="font-size:12px;color:#888;margin-top:6px;">{deal["departure_date"]} &rarr; {deal.get("return_date", "")}</div>
            <a href="{delta_url}" style="display:inline-block;margin-top:10px;padding:6px 14px;
               font-size:11px;font-weight:bold;color:#fff;background:{badge_bg};
               text-decoration:none;border-radius:6px;">BOOK ON DELTA &rarr;</a>
          </td>
          <td style="vertical-align:top;text-align:right;width:120px;">
            <div style="font-size:36px;font-weight:bold;color:{border};">${deal["price"]}</div>
            <div style="font-size:10px;color:#888;">roundtrip</div>
          </td>
        </tr></table>
      </div>
    </div>
    """

def send_email(deals, scan_summary):
    if not deals or not GMAIL_APP_PASSWORD or not GMAIL_ADDRESS:
        return False
    try:
        mistakes = [d for d in deals if "MISTAKE" in d["type"]]
        great_deals = [d for d in deals if "GREAT DEAL" in d["type"]]
        prefix = "MISTAKE FARE" if mistakes else "Deal Alert"
        subject = f"{prefix}: {len(deals)} Delta ATL flights found!"
        scan_date = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p UTC")

        html = f"""<html><body style="margin:0;padding:0;background:#f0f0f0;font-family:Arial,sans-serif;">
<div style="max-width:640px;margin:0 auto;background:#fff;">
  <div style="background:linear-gradient(135deg,#003366,#001a33);padding:28px 24px;text-align:center;">
    <div style="font-size:12px;color:#80b3ff;letter-spacing:2px;text-transform:uppercase;">Weekly Scan Report</div>
    <div style="font-size:26px;font-weight:bold;color:#fff;margin-top:6px;">Delta ATL Deal Scanner</div>
    <div style="font-size:12px;color:#99ccff;margin-top:4px;">{scan_date}</div>
  </div>
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#fafafa;border-bottom:1px solid #e0e0e0;">
    <tr>
      <td style="text-align:center;padding:14px;border-right:1px solid #e0e0e0;">
        <div style="font-size:26px;font-weight:bold;color:#003366;">{scan_summary['destinations_scanned']}</div>
        <div style="font-size:10px;color:#888;text-transform:uppercase;">Routes</div>
      </td>
      <td style="text-align:center;padding:14px;border-right:1px solid #e0e0e0;">
        <div style="font-size:26px;font-weight:bold;color:#d32f2f;">{len(mistakes)}</div>
        <div style="font-size:10px;color:#888;text-transform:uppercase;">Mistakes</div>
      </td>
      <td style="text-align:center;padding:14px;">
        <div style="font-size:26px;font-weight:bold;color:#2e7d32;">{len(great_deals)}</div>
        <div style="font-size:10px;color:#888;text-transform:uppercase;">Deals</div>
      </td>
    </tr>
  </table>
  <div style="padding:24px;">
"""
        if mistakes:
            html += '<div style="font-size:11px;color:#d32f2f;font-weight:bold;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #d32f2f;">MISTAKE FARES - ACT IMMEDIATELY</div>'
            for d in sorted(mistakes, key=lambda x: x["price"]):
                html += _email_card(d)

        if great_deals:
            html += '<div style="font-size:11px;color:#2e7d32;font-weight:bold;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:12px;margin-top:24px;padding-bottom:8px;border-bottom:2px solid #2e7d32;">GREAT DEALS</div>'
            for d in sorted(great_deals, key=lambda x: x["price"]):
                html += _email_card(d)

        html += """
  </div>
  <div style="background:#003366;color:#99ccff;padding:18px 24px;text-align:center;font-size:11px;">
    Delta ATL Nonstop Scanner &middot; 60 routes &middot; Weekly<br>
    Prices roundtrip Main Cabin &middot; <a href="https://www.delta.com" style="color:#80b3ff;">delta.com</a>
  </div>
</div></body></html>"""

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = GMAIL_ADDRESS
        message["To"] = GMAIL_ADDRESS
        message.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, GMAIL_ADDRESS, message.as_string())
        print(f"  Email sent with {len(deals)} deals!", flush=True)
        return True
    except Exception as e:
        print(f"  Email error: {e}", flush=True)
        return False


# ── HTML DASHBOARD ───────────────────────────────────────────────────────────

def generate_dashboard(deals, scan_summary, all_prices):
    scan_date = datetime.now().strftime("%B %d, %Y at %I:%M %p UTC")
    mistakes = [d for d in deals if "MISTAKE" in d["type"]]
    great_deals = [d for d in deals if "GREAT DEAL" in d["type"]]

    region_stats = {}
    for code, info in DESTINATIONS.items():
        r = info["region"]
        if r not in region_stats:
            region_stats[r] = {"count": 0, "deals": 0, "threshold": THRESHOLDS[r]["deal"]}
        region_stats[r]["count"] += 1
    for d in deals:
        r = d["region"]
        if r in region_stats:
            region_stats[r]["deals"] += 1

    # Build deal cards HTML
    deal_cards_html = ""
    if not deals:
        deal_cards_html = """
    <div style="text-align:center;padding:60px 20px;color:#5a6a7a;">
        <div style="font-size:48px;margin-bottom:16px;">&#x1f4ed;</div>
        <div style="font-size:18px;color:#7a8a9a;">No deals found this week</div>
        <div style="font-size:13px;margin-top:8px;">All 60 routes scanned. Prices above thresholds.</div>
        <div style="font-size:13px;margin-top:4px;">Next scan: Tuesday 6 AM ET</div>
    </div>
"""
    else:
        if mistakes:
            deal_cards_html += '<div class="sec-title red">MISTAKE FARES - BOOK IMMEDIATELY</div><div class="cards">\n'
            for d in sorted(mistakes, key=lambda x: x["price"]):
                deal_cards_html += _dash_card(d, True)
            deal_cards_html += '</div>\n'
        if great_deals:
            deal_cards_html += '<div class="sec-title green">GREAT DEALS</div><div class="cards">\n'
            for d in sorted(great_deals, key=lambda x: x["price"]):
                deal_cards_html += _dash_card(d, False)
            deal_cards_html += '</div>\n'

    # Region overview cards
    region_html = ""
    for region in ["caribbean", "mexico", "central_america", "south_america",
                    "canada", "europe", "africa", "middle_east", "asia"]:
        if region not in region_stats:
            continue
        s = region_stats[region]
        dc = s["deals"]
        cls = "" if dc > 0 else " none"
        region_html += f"""
        <div class="rcard">
            <div class="rname">{region.replace("_"," ").title()}</div>
            <div class="rdetail">{s["count"]} routes &middot; Deal &lt; ${s["threshold"]}</div>
            <div class="rdeals{cls}">{dc} deal{"s" if dc != 1 else ""}</div>
        </div>
"""

    # Thresholds table
    thresh_rows = ""
    for region in ["canada","mexico","caribbean","central_america","south_america","europe","africa","middle_east","asia"]:
        t = THRESHOLDS[region]
        thresh_rows += f'<tr><td>{region.replace("_"," ").title()}</td><td>${t["deal"]}</td><td>${t["mistake"]}</td></tr>\n'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Delta ATL Deal Scanner</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'DM Sans',sans-serif;background:#0a0e1a;color:#e0e0e0;min-height:100vh}}
.hdr{{background:linear-gradient(135deg,#0d1b2a,#1b2838,#0d1b2a);border-bottom:1px solid rgba(255,255,255,.06);padding:32px 24px;text-align:center}}
.hdr-label{{font-size:11px;color:#4a9eff;letter-spacing:3px;text-transform:uppercase;font-weight:500}}
.hdr-title{{font-size:32px;font-weight:700;color:#fff;margin-top:8px}}
.hdr-sub{{font-size:13px;color:#6b7b8d;margin-top:6px}}
.stats{{display:flex;justify-content:center;background:#0f1520;border-bottom:1px solid rgba(255,255,255,.04);flex-wrap:wrap}}
.st{{padding:20px 32px;text-align:center;border-right:1px solid rgba(255,255,255,.04);min-width:120px}}
.st:last-child{{border-right:none}}
.st-v{{font-size:32px;font-weight:700;font-family:'JetBrains Mono',monospace}}
.st-l{{font-size:10px;color:#5a6a7a;text-transform:uppercase;letter-spacing:1.5px;margin-top:4px}}
.blue{{color:#4a9eff}}.red{{color:#ff4444}}.green{{color:#44cc66}}.yellow{{color:#ffcc00}}
.wrap{{max-width:1100px;margin:0 auto;padding:24px}}
.sec-title{{font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin:32px 0 16px;padding-bottom:8px;border-bottom:1px solid rgba(255,255,255,.08)}}
.sec-title.red{{color:#ff4444;border-color:#ff4444}}.sec-title.green{{color:#44cc66;border-color:#44cc66}}.sec-title.blue{{color:#4a9eff;border-color:#4a9eff}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}}
.card{{background:#141c2b;border:1px solid rgba(255,255,255,.06);border-radius:12px;overflow:hidden;transition:transform .2s,border-color .2s}}
.card:hover{{transform:translateY(-2px);border-color:rgba(255,255,255,.15)}}
.card.mk{{border-color:rgba(255,68,68,.3)}}.card.mk:hover{{border-color:rgba(255,68,68,.6)}}
.cbadge{{padding:6px 16px;font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase}}
.cbadge.mk{{background:#ff4444;color:#fff}}.cbadge.dl{{background:#1a3d1a;color:#44cc66}}
.cbody{{padding:16px 20px 20px;display:flex;justify-content:space-between;align-items:flex-start}}
.croute{{font-size:11px;color:#5a6a7a}}.cdest{{font-size:20px;font-weight:700;color:#fff;margin-top:2px}}
.cname{{font-size:13px;color:#7a8a9a;margin-top:2px}}.cdate{{font-size:12px;color:#5a6a7a;margin-top:8px}}
.cprice{{text-align:right}}.cpv{{font-size:32px;font-weight:700;font-family:'JetBrains Mono',monospace}}
.cpv.red{{color:#ff4444}}.cpv.green{{color:#44cc66}}.cpl{{font-size:10px;color:#5a6a7a;text-transform:uppercase}}
.cbook{{display:inline-block;margin-top:10px;padding:6px 14px;font-size:11px;font-weight:700;text-decoration:none;border-radius:6px;text-transform:uppercase;letter-spacing:.5px}}
.cbook.mk{{background:#ff4444;color:#fff}}.cbook.dl{{background:#1a3d1a;color:#44cc66;border:1px solid #44cc66}}
.rgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}}
.rcard{{background:#141c2b;border:1px solid rgba(255,255,255,.06);border-radius:10px;padding:16px}}
.rname{{font-size:13px;font-weight:600;color:#8a9aaa}}.rdetail{{font-size:12px;color:#5a6a7a;margin-top:4px}}
.rdeals{{font-size:20px;font-weight:700;color:#44cc66;margin-top:8px;font-family:'JetBrains Mono',monospace}}.rdeals.none{{color:#3a4a5a}}
.ttable{{width:100%;border-collapse:collapse;margin-top:12px}}
.ttable th,.ttable td{{padding:8px 12px;text-align:left;font-size:13px;border-bottom:1px solid rgba(255,255,255,.04)}}
.ttable th{{color:#5a6a7a;font-size:10px;text-transform:uppercase;letter-spacing:1px}}.ttable td{{color:#8a9aaa}}
.footer{{text-align:center;padding:32px;font-size:11px;color:#3a4a5a;border-top:1px solid rgba(255,255,255,.04);margin-top:40px}}
.footer a{{color:#4a9eff;text-decoration:none}}
@media(max-width:600px){{.cards{{grid-template-columns:1fr}}.rgrid{{grid-template-columns:1fr 1fr}}.stats{{flex-wrap:wrap}}.st{{flex:1;min-width:50%}}}}
</style>
</head>
<body>
<div class="hdr">
  <div class="hdr-label">Weekly Scan Report</div>
  <div class="hdr-title">Delta ATL Deal Scanner</div>
  <div class="hdr-sub">{scan_date} &middot; {len(DESTINATIONS)} nonstop international routes</div>
</div>
<div class="stats">
  <div class="st"><div class="st-v blue">{scan_summary['destinations_scanned']}</div><div class="st-l">Routes Scanned</div></div>
  <div class="st"><div class="st-v yellow">{scan_summary['api_calls']}</div><div class="st-l">API Calls</div></div>
  <div class="st"><div class="st-v red">{len(mistakes)}</div><div class="st-l">Mistake Fares</div></div>
  <div class="st"><div class="st-v green">{len(great_deals)}</div><div class="st-l">Great Deals</div></div>
</div>
<div class="wrap">
{deal_cards_html}
<div class="sec-title blue">REGION OVERVIEW</div>
<div class="rgrid">
{region_html}
</div>
<div class="sec-title blue">PRICE THRESHOLDS (ROUNDTRIP MAIN CABIN)</div>
<table class="ttable">
<tr><th>Region</th><th>Deal Under</th><th>Mistake Under</th></tr>
{thresh_rows}
</table>
<div class="footer">
  Delta ATL Nonstop Scanner &middot; SerpAPI + GitHub Actions<br>
  Prices roundtrip Main Cabin &middot; <a href="https://www.delta.com">delta.com</a><br>
  Scans weekly on Tuesdays at 6 AM ET
</div>
</div>
</body></html>"""

    with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  Dashboard saved to {DASHBOARD_FILE}", flush=True)


def _dash_card(deal, is_mistake):
    cls = "card mk" if is_mistake else "card"
    badge = "cbadge mk" if is_mistake else "cbadge dl"
    badge_txt = "MISTAKE FARE - BOOK NOW" if is_mistake else "GREAT DEAL"
    pv = "cpv red" if is_mistake else "cpv green"
    bk = "cbook mk" if is_mistake else "cbook dl"
    flag = deal.get("flag", "")
    region = deal["region"].replace("_", " ").title()
    delta_url = (
        f"https://www.delta.com/flight-search/search?cacheKeySuffix=a"
        f"&fromCity=ATL&toCity={deal['destination']}"
        f"&departureDate={deal['departure_date']}"
        f"&returnDate={deal.get('return_date', '')}"
        f"&tripType=ROUND_TRIP&paxCount=1&cabinType=MAIN"
    )
    return f"""<div class="{cls}">
  <div class="{badge}">{badge_txt}</div>
  <div class="cbody">
    <div>
      <div class="croute">{flag} {region}</div>
      <div class="cdest">ATL &harr; {deal["destination"]}</div>
      <div class="cname">{deal["destination_name"]}</div>
      <div class="cdate">{deal["departure_date"]} &rarr; {deal.get("return_date", "")}</div>
      <a href="{delta_url}" target="_blank" class="{bk}">Book on Delta &rarr;</a>
    </div>
    <div class="cprice">
      <div class="{pv}">${deal["price"]}</div>
      <div class="cpl">roundtrip</div>
    </div>
  </div>
</div>
"""


# ── MAIN SCAN ────────────────────────────────────────────────────────────────

def scan_for_deals():
    scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    print("=" * 60)
    print("Delta ATL International Nonstop Scanner")
    print(scan_time)
    print(f"{len(DESTINATIONS)} destinations across 9 regions")
    print("=" * 60)

    regions = {}
    for code, info in DESTINATIONS.items():
        r = info["region"]
        regions[r] = regions.get(r, 0) + 1
    for r, count in sorted(regions.items()):
        t = THRESHOLDS[r]
        rname = r.replace('_', ' ').title()
        print(f"  {rname:20s} {count:2d} routes  |  Deal < ${t['deal']}  |  Mistake < ${t['mistake']}")
    print()

    sent_alerts = load_sent_alerts()
    all_deals = []
    all_prices = []
    new_alerts = []
    total_calls = 0

    check_dates = [14, 60, 120]

    for days_out in check_dates:
        departure_date = (datetime.now() + timedelta(days=days_out)).strftime("%Y-%m-%d")
        print(f"\nChecking {days_out} days out ({departure_date})...")

        for dest_code, dest_info in DESTINATIONS.items():
            region = dest_info["region"]
            trip_days = THRESHOLDS[region].get("trip_days", 7)
            return_date = (datetime.now() + timedelta(days=days_out + trip_days)).strftime("%Y-%m-%d")

            data = search_flights(ORIGIN, dest_code, departure_date, return_date)
            total_calls += 1

            if data:
                for fg in ["best_flights", "other_flights"]:
                    for flight in data.get(fg, []):
                        if is_nonstop_delta(flight) and flight.get("price"):
                            all_prices.append({
                                "destination": dest_code,
                                "region": dest_info["region"],
                                "price": flight["price"],
                                "date": departure_date,
                            })

                deals = parse_flights(data, dest_code, dest_info, departure_date, return_date)
                for deal in deals:
                    alert_key = f"{deal['destination']}-{deal['price']}-{deal['departure_date']}"
                    if alert_key not in sent_alerts:
                        all_deals.append(deal)
                        new_alerts.append(alert_key)
                        tag = "!!" if "MISTAKE" in deal["type"] else "--"
                        print(f"    {tag} {dest_info['name']} {departure_date}-{return_date} ${deal['price']} ({deal['type']})", flush=True)

    scan_summary = {
        "scan_date": scan_time,
        "destinations_scanned": len(DESTINATIONS),
        "api_calls": total_calls,
        "deals_found": len(new_alerts),
        "mistakes_found": len([d for d in all_deals if "MISTAKE" in d["type"]]),
    }

    print()
    print("=" * 60)
    print("Scan Summary")
    print(f"   API calls used:    {total_calls}")
    print(f"   Budget remaining:  ~{1000 - total_calls} this month (est.)")
    print(f"   New deals found:   {len(new_alerts)}")
    print(f"   Total prices seen: {len(all_prices)}")
    print("=" * 60)

    if new_alerts:
        sent_alerts.update(new_alerts)
        save_sent_alerts(sent_alerts)

    # Save history
    history = load_scan_history()
    history["scans"].append({"summary": scan_summary, "deals": all_deals})
    if len(history["scans"]) > 12:
        history["scans"] = history["scans"][-12:]
    save_scan_history(history)

    # Always generate dashboard
    print("\nGenerating dashboard...")
    generate_dashboard(all_deals, scan_summary, all_prices)

    # Email only when deals exist
    if all_deals:
        print(f"\n{len(all_deals)} deals found - sending email...")
        send_email(all_deals, scan_summary)
        return True
    else:
        print("\nNo deals this scan. Dashboard updated. Next scan: next Tuesday.")
        return False


if __name__ == "__main__":
    scan_for_deals()
    sys.exit(0)
