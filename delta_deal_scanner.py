#!/usr/bin/env python3
"""
Delta ATL Flight Deal & Mistake Fare Scanner
Hunts for BOTH regular deals AND mistake fares on nonstop Delta from ATL
Regular deals: $200 domestic / $450 international
Mistake fares: Under $100 domestic / $250 international
Sends email alerts immediately when deals found
Runs 4x daily via GitHub Actions
"""

import os
import json
import requests
import sys
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")

if not SERPAPI_KEY:
    print("ERROR: SERPAPI_KEY not set")
    sys.exit(1)

# Price thresholds
DOMESTIC_THRESHOLD = 200           # Regular deal threshold
DOMESTIC_MISTAKE = 100             # Likely mistake threshold
INTERNATIONAL_THRESHOLD = 450      # Regular deal threshold
INTERNATIONAL_MISTAKE = 250        # Likely mistake threshold
ORIGIN = "ATL"

# 21 Curated Safe Destinations
CARIBBEAN = {
    "SJU": "Puerto Rico",
    "PLS": "Turks & Caicos",
    "AUA": "Aruba",
    "CYM": "Cayman Islands",
    "MBJ": "Jamaica - Montego Bay",
    "PUJ": "Dominican Republic - Punta Cana",
    "NAS": "Bahamas - Nassau",
    "UVF": "Saint Lucia",
    "GND": "Grenada",
    "BGI": "Barbados",
    "SXM": "Saint Maarten",
}

CENTRAL_AMERICA = {
    "SJO": "Costa Rica",
    "BZE": "Belize",
    "PTY": "Panama",
    "MGA": "Nicaragua - Managua",
}

MEXICO = {
    "CUN": "Cancun/Playa del Carmen",
    "PVR": "Puerto Vallarta",
    "SJD": "Los Cabos",
    "MEX": "Mexico City",
}

NORTH_AMERICA = {
    "YYZ": "Toronto, Canada",
    "YVR": "Vancouver, Canada",
}

ALL_DESTINATIONS = {**CARIBBEAN, **CENTRAL_AMERICA, **MEXICO, **NORTH_AMERICA}

SENT_ALERTS_FILE = "/tmp/delta_deals.json"

def load_sent_alerts():
    """Load previously alerted deals"""
    if os.path.exists(SENT_ALERTS_FILE):
        try:
            with open(SENT_ALERTS_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_sent_alerts(alerts):
    """Save alerted deals"""
    with open(SENT_ALERTS_FILE, 'w') as f:
        json.dump(list(alerts), f)

def search_flights(origin, destination, departure_date):
    """Search flights using SerpAPI"""
    url = "https://serpapi.com/search"
    
    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": departure_date,
        "type": "1",
        "api_key": SERPAPI_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Error {origin}→{destination}: {str(e)[:40]}", flush=True)
        return None

def is_nonstop_delta(flight):
    """Verify nonstop Delta flight"""
    try:
        airline = flight.get("airline", "")
        if "Delta" not in airline:
            return False
        
        stops = flight.get("stops", None)
        if stops is None:
            segments = flight.get("segments", [])
            if len(segments) > 1:
                return False
        elif stops > 0:
            return False
        
        return True
    except:
        return False

def classify_deal(price, is_international):
    """Classify deal as mistake, great, or ignore"""
    if is_international:
        if price < INTERNATIONAL_MISTAKE:
            return "🚨 LIKELY MISTAKE"
        elif price < INTERNATIONAL_THRESHOLD:
            return "💰 GREAT DEAL"
    else:
        if price < DOMESTIC_MISTAKE:
            return "🚨 LIKELY MISTAKE"
        elif price < DOMESTIC_THRESHOLD:
            return "💰 GREAT DEAL"
    
    return None

def parse_flights_response(data, destination, dest_name, is_international, departure_date):
    """Extract deals from response"""
    deals = []
    
    if not data or "best_flights" not in data:
        return deals
    
    threshold = INTERNATIONAL_THRESHOLD if is_international else DOMESTIC_THRESHOLD
    
    for flight in data.get("best_flights", []):
        try:
            if not is_nonstop_delta(flight):
                continue
            
            price = flight.get("price")
            if not price or price >= threshold:
                continue
            
            deal_type = classify_deal(price, is_international)
            if not deal_type:
                continue
            
            deal = {
                "origin": "ATL",
                "destination": destination,
                "destination_name": dest_name,
                "price": price,
                "type": deal_type,
                "departure_date": departure_date,
                "is_international": is_international,
                "found_at": datetime.now().isoformat()
            }
            deals.append(deal)
        except:
            continue
    
    return deals

def send_email(deals):
    """Send email alert via Gmail SMTP"""
    if not deals or not GMAIL_APP_PASSWORD or not GMAIL_ADDRESS:
        return False
    
    try:
        # Separate by type
        mistakes = [d for d in deals if "LIKELY MISTAKE" in d["type"]]
        great_deals = [d for d in deals if "GREAT DEAL" in d["type"]]
        
        # Build HTML email
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #d32f2f;">🎯 Delta ATL Flight Deal Alert</h2>
            <p><strong>Found at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>
        """
        
        if mistakes:
            html += f"""
            <h3 style="color: #d32f2f;">🚨 LIKELY MISTAKES (ACT FAST!)</h3>
            <table border="1" cellpadding="10" style="border-collapse: collapse;">
              <tr style="background-color: #f5f5f5;">
                <th>Route</th>
                <th>Destination</th>
                <th>Departure</th>
                <th>Price</th>
              </tr>
            """
            for deal in sorted(mistakes, key=lambda x: x["price"]):
                html += f"""
              <tr>
                <td>{deal['origin']} → {deal['destination']}</td>
                <td>{deal['destination_name']}</td>
                <td>{deal['departure_date']}</td>
                <td style="color: #d32f2f; font-weight: bold;">${deal['price']}</td>
              </tr>
                """
            html += "</table><br>"
        
        if great_deals:
            html += f"""
            <h3 style="color: #388e3c;">💰 GREAT DEALS</h3>
            <table border="1" cellpadding="10" style="border-collapse: collapse;">
              <tr style="background-color: #f5f5f5;">
                <th>Route</th>
                <th>Destination</th>
                <th>Departure</th>
                <th>Price</th>
              </tr>
            """
            for deal in sorted(great_deals, key=lambda x: x["price"]):
                html += f"""
              <tr>
                <td>{deal['origin']} → {deal['destination']}</td>
                <td>{deal['destination_name']}</td>
                <td>{deal['departure_date']}</td>
                <td style="color: #388e3c; font-weight: bold;">${deal['price']}</td>
              </tr>
                """
            html += "</table><br>"
        
        html += """
            <p style="font-size: 12px; color: #666;">
              <em>Delta ATL nonstop scanner running 4x daily. 
              Book immediately—deals disappear fast!</em>
            </p>
          </body>
        </html>
        """
        
        # Send email
        message = MIMEMultipart("alternative")
        message["Subject"] = f"✈️ Delta Deal Alert: {len(deals)} flights found"
        message["From"] = GMAIL_ADDRESS
        message["To"] = GMAIL_ADDRESS
        
        part = MIMEText(html, "html")
        message.attach(part)
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, GMAIL_ADDRESS, message.as_string())
        
        print(f"✅ Email sent with {len(deals)} deals", flush=True)
        return True
    except Exception as e:
        print(f"❌ Email error: {e}", flush=True)
        return False

def scan_for_deals():
    """Main scanning function"""
    scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"\n🎯 Delta ATL Deal Scanner - {scan_time}")
    print(f"Checking {len(ALL_DESTINATIONS)} destinations for deals (today-7 days)")
    print("-" * 60)
    
    sent_alerts = load_sent_alerts()
    all_deals = []
    new_alerts = []
    
    # Check TODAY and NEXT 7 DAYS
    check_days = [0, 1, 2, 3, 4, 5, 6, 7]
    total_calls = 0
    
    for days_out in check_days:
        departure_date = (datetime.now() + timedelta(days=days_out)).strftime("%Y-%m-%d")
        date_label = "TODAY" if days_out == 0 else f"+{days_out}d"
        
        for destination, dest_name in ALL_DESTINATIONS.items():
            is_intl = destination not in ["YYZ", "YVR"]
            
            data = search_flights(ORIGIN, destination, departure_date)
            total_calls += 1
            
            if data:
                deals = parse_flights_response(data, destination, dest_name, is_intl, departure_date)
                
                for deal in deals:
                    alert_key = f"{deal['origin']}-{deal['destination']}-{deal['price']}-{deal['departure_date']}"
                    if alert_key not in sent_alerts:
                        all_deals.append(deal)
                        new_alerts.append(alert_key)
                        
                        if "LIKELY MISTAKE" in deal["type"]:
                            print(f"    🚨 MISTAKE: {dest_name} {departure_date} - ${deal['price']}!!!", flush=True)
                        else:
                            print(f"    💰 DEAL: {dest_name} {departure_date} - ${deal['price']}", flush=True)
    
    print(f"\nAPI calls used: {total_calls} | New deals: {len(new_alerts)}")
    
    # Save alerts
    if new_alerts:
        sent_alerts.update(new_alerts)
        save_sent_alerts(sent_alerts)
    
    # Send email if deals found
    if all_deals:
        print(f"\n✅ Found {len(all_deals)} deals - sending email...")
        send_email(all_deals)
        return True
    else:
        print("\n❌ No deals found this scan")
        return False

if __name__ == "__main__":
    success = scan_for_deals()
    sys.exit(0 if success else 1)
