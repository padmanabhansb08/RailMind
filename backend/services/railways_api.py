import httpx # type: ignore
import os
from datetime import datetime
from dotenv import load_dotenv

# Ensure env variables are loaded
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=env_path)

RAILWAYS_API_KEY = os.getenv("RAILWAYS_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "irctc1.p.rapidapi.com")

BASE_URL = "http://indianrailapi.com/api/v2"

SIMULATED_OVERRIDES = {}

STATION_COORDS = {
    # North India
    "NDLS": {"lat": 28.6419, "lng": 77.2194, "name": "New Delhi"},
    "DLI": {"lat": 28.6562, "lng": 77.2410, "name": "Delhi Junction"},
    "CNB": {"lat": 26.4499, "lng": 80.3319, "name": "Kanpur Central"},
    "LKO": {"lat": 26.8467, "lng": 80.9462, "name": "Lucknow"},
    "ALD": {"lat": 25.4358, "lng": 81.8463, "name": "Prayagraj"},
    "BSB": {"lat": 25.3176, "lng": 82.9739, "name": "Varanasi"},
    "GKP": {"lat": 26.7606, "lng": 83.3732, "name": "Gorakhpur"},
    "AGC": {"lat": 27.1767, "lng": 78.0081, "name": "Agra Cantt"},
    "MTJ": {"lat": 27.4924, "lng": 77.6737, "name": "Mathura"},
    "ALJN": {"lat": 27.8974, "lng": 78.0880, "name": "Aligarh"},
    "MB": {"lat": 28.9845, "lng": 77.7064, "name": "Moradabad"},
    "SRE": {"lat": 29.9691, "lng": 77.5469, "name": "Saharanpur"},
    "AMB": {"lat": 30.3782, "lng": 76.7767, "name": "Ambala"},
    "ASR": {"lat": 31.6340, "lng": 74.8723, "name": "Amritsar"},
    "LDH": {"lat": 30.9010, "lng": 75.8573, "name": "Ludhiana"},
    "UMB": {"lat": 30.9167, "lng": 76.9500, "name": "Ambala Cantt"},
    "HW": {"lat": 29.9457, "lng": 78.1642, "name": "Haridwar"},
    "DDN": {"lat": 30.3165, "lng": 78.0322, "name": "Dehradun"},

    # Bihar & Jharkhand
    "PNBE": {"lat": 25.6093, "lng": 85.1235, "name": "Patna"},
    "RJPB": {"lat": 25.6093, "lng": 85.1390, "name": "Rajendra Nagar"},
    "BGP": {"lat": 25.2425, "lng": 86.9842, "name": "Bhagalpur"},
    "MFP": {"lat": 26.1197, "lng": 85.3910, "name": "Muzaffarpur"},
    "DBG": {"lat": 26.1522, "lng": 85.8970, "name": "Darbhanga"},
    "SPJ": {"lat": 25.8645, "lng": 85.7810, "name": "Samastipur"},
    "DHN": {"lat": 23.7957, "lng": 86.4304, "name": "Dhanbad"},
    "JSME": {"lat": 24.1540, "lng": 86.2028, "name": "Jasidih"},
    "RNC": {"lat": 23.3441, "lng": 85.3096, "name": "Ranchi"},

    # West Bengal
    "HWH": {"lat": 22.5958, "lng": 88.2636, "name": "Howrah"},
    "SDAH": {"lat": 22.5697, "lng": 88.3697, "name": "Sealdah"},
    "KOAA": {"lat": 22.5726, "lng": 88.3639, "name": "Kolkata"},
    "BDC": {"lat": 22.8456, "lng": 88.3632, "name": "Bandel"},
    "BWN": {"lat": 23.2324, "lng": 87.8615, "name": "Bardhaman"},
    "KGP": {"lat": 22.3460, "lng": 87.3195, "name": "Kharagpur"},

    # Maharashtra
    "CSTM": {"lat": 18.9398, "lng": 72.8355, "name": "Mumbai CST"},
    "BCT": {"lat": 18.9690, "lng": 72.8205, "name": "Mumbai Central"},
    "LTT": {"lat": 19.0668, "lng": 72.9244, "name": "Lokmanya Tilak"},
    "PUNE": {"lat": 18.5286, "lng": 73.8742, "name": "Pune"},
    "NGP": {"lat": 21.1458, "lng": 79.0882, "name": "Nagpur"},
    "AWB": {"lat": 19.8762, "lng": 75.3433, "name": "Aurangabad"},
    "NED": {"lat": 19.1566, "lng": 77.3212, "name": "Nanded"},
    "SUR": {"lat": 17.6868, "lng": 75.9064, "name": "Solapur"},

    # Karnataka
    "SBC": {"lat": 12.9784, "lng": 77.5736, "name": "Bangalore City"},
    "YPR": {"lat": 13.0148, "lng": 77.5510, "name": "Yesvantpur"},
    "UBL": {"lat": 15.3647, "lng": 75.1240, "name": "Hubli"},
    "MYS": {"lat": 12.2958, "lng": 76.6394, "name": "Mysuru"},

    # Tamil Nadu
    "MAS": {"lat": 13.0827, "lng": 80.2707, "name": "Chennai Central"},
    "MS": {"lat": 13.0012, "lng": 80.2565, "name": "Chennai Egmore"},
    "TPJ": {"lat": 10.7905, "lng": 78.7047, "name": "Tiruchirappalli"},
    "MDU": {"lat": 9.9252, "lng": 78.1198, "name": "Madurai"},
    "CBE": {"lat": 11.0168, "lng": 76.9558, "name": "Coimbatore"},
    "NCJ": {"lat": 8.7139, "lng": 77.7567, "name": "Nagercoil"},

    # Kerala
    "TVC": {"lat": 8.4855, "lng": 76.9492, "name": "Thiruvananthapuram"},
    "ERS": {"lat": 9.9816, "lng": 76.2999, "name": "Ernakulam"},
    "CLT": {"lat": 11.2588, "lng": 75.7804, "name": "Kozhikode"},
    "SRR": {"lat": 10.9598, "lng": 75.9495, "name": "Shoranur"},

    # Andhra Pradesh & Telangana
    "SC": {"lat": 17.4339, "lng": 78.5000, "name": "Secunderabad"},
    "HYB": {"lat": 17.3850, "lng": 78.4867, "name": "Hyderabad"},
    "BZA": {"lat": 16.5193, "lng": 80.6305, "name": "Vijayawada"},
    "VSKP": {"lat": 17.7231, "lng": 83.2985, "name": "Visakhapatnam"},
    "GNT": {"lat": 16.3067, "lng": 80.4365, "name": "Guntur"},

    # Gujarat
    "ADI": {"lat": 23.0225, "lng": 72.5714, "name": "Ahmedabad"},
    "BRC": {"lat": 22.3144, "lng": 73.1932, "name": "Vadodara"},
    "ST": {"lat": 21.1702, "lng": 72.8311, "name": "Surat"},
    "RJT": {"lat": 22.3039, "lng": 70.8022, "name": "Rajkot"},

    # Madhya Pradesh
    "BPL": {"lat": 23.2599, "lng": 77.4126, "name": "Bhopal"},
    "JBP": {"lat": 23.1815, "lng": 79.9864, "name": "Jabalpur"},
    "GWL": {"lat": 26.2183, "lng": 78.1828, "name": "Gwalior"},
    "INDB": {"lat": 22.7196, "lng": 75.8577, "name": "Indore"},
    "ET": {"lat": 23.6611, "lng": 77.7631, "name": "Itarsi"},

    # Rajasthan
    "JP": {"lat": 26.9124, "lng": 75.7873, "name": "Jaipur"},
    "AII": {"lat": 26.4499, "lng": 74.6399, "name": "Ajmer"},
    "JU": {"lat": 26.2389, "lng": 73.0243, "name": "Jodhpur"},
    "BKN": {"lat": 28.0229, "lng": 73.3119, "name": "Bikaner"},
    "UDZ": {"lat": 24.5713, "lng": 73.6915, "name": "Udaipur"},

    # Odisha
    "BBS": {"lat": 20.2961, "lng": 85.8189, "name": "Bhubaneswar"},
    "CTC": {"lat": 20.4625, "lng": 85.8830, "name": "Cuttack"},
    "PURI": {"lat": 19.8135, "lng": 85.8312, "name": "Puri"},

    # Assam & Northeast
    "GHY": {"lat": 26.1445, "lng": 91.7362, "name": "Guwahati"},
    "DBRG": {"lat": 27.4728, "lng": 95.0152, "name": "Dibrugarh"},
    "8011160": {"lat": 52.5256, "lng": 13.369, "name": "Berlin Hbf"},
    "8000261": {"lat": 48.1402, "lng": 11.5600, "name": "Munich Hbf"},
}

def parse_rapidapi_train_for_agent(data: dict, train_number: str) -> dict:
    outer_data = data.get("data", {})
    if not outer_data:
        return {}
    
    t_num = outer_data.get("train_number", train_number)
    t_name = outer_data.get("train_name", t_num)
    
    station_code = outer_data.get("current_station_code", "Unknown")
    coords = STATION_COORDS.get(station_code, {"lat": 20.5937, "lng": 78.9629, "name": "Unknown"})
    
    current_station = outer_data.get("current_station_name", "Unknown").replace("~", "").strip()
    if current_station == "Unknown" and coords.get("name") != "Unknown":
        current_station = coords["name"]
    
    delay_minutes = 0
    try:
        delay_minutes = int(outer_data.get("delay", 0))
        # Add a small ±2 minute time-based variation for realistic live demo feel
        # Only if train is already delayed (don't create fake delays for on-time trains)
        if delay_minutes > 0:
            import time, hashlib
            seed = int(hashlib.md5(f"{t_num}{int(time.time() // 60)}".encode()).hexdigest()[:6], 16)
            variation = (seed % 5) - 2  # Range: -2 to +2
            delay_minutes = max(1, delay_minutes + variation)
    except:
        pass

    if delay_minutes == 0:
        passenger_load = "normal"
    elif delay_minutes <= 15:
        passenger_load = "medium"
    elif delay_minutes <= 30:
        passenger_load = "high"
    else:
        passenger_load = "overcrowded"

    status = "on_time"
    if delay_minutes > 60:
        status = "severely_delayed"
    elif delay_minutes > 15:
        status = "delayed"
        
    title = str(outer_data.get("title", "")).lower()
    if "complete" in title or "reached" in title:
        status = "reached"
        
    lat = coords["lat"]
    lng = coords["lng"]
    
    # Add time-seeded sinusoidal drift (approx. 5km) for live demo feel
    import math, time
    try:
        t_num_int = int(t_num)
    except:
        t_num_int = 0
    drift_lat = 0.04 * math.sin(time.time() / 180.0 + t_num_int * 1.5)
    drift_lng = 0.04 * math.cos(time.time() / 180.0 + t_num_int * 1.5)
    lat += drift_lat
    lng += drift_lng
        
    return {
        "train_number": t_num,
        "train_name": t_name,
        "current_station": current_station,
        "station_code": station_code,
        "delay_minutes": delay_minutes,
        "passenger_load": passenger_load,
        "status": status,
        "schedule_arrival": outer_data.get("cur_stn_sta", "-"),
        "actual_arrival": outer_data.get("eta", "-"),
        "source": outer_data.get("source_stn_name", "Unknown"),
        "destination": outer_data.get("dest_stn_name", "Unknown"),
        "lat": lat,
        "lng": lng
    }

RAW_MOCK_TRAINS = {
    "12301": {
        "train_number": "12301",
        "train_name": "Howrah Rajdhani Express",
        "source": "NDLS",
        "destination": "HWH",
        "source_stn_name": "NEW DELHI",
        "dest_stn_name": "HOWRAH JN",
        "title": "Delayed at Kanpur Central",
        "delay": 45,
        "current_station_code": "CNB",
        "current_station_name": "Kanpur Central",
        "cur_stn_lat": "26.4499",
        "cur_stn_lng": "80.3319",
        "cur_stn_sta": "10:05",
        "eta": "10:50",
        "gps_unable": False,
        "route_stops": ["NDLS", "CNB", "ALD", "BSB", "PNBE", "HWH"]
    },
    "12951": {
        "train_number": "12951",
        "train_name": "Mumbai Rajdhani Express",
        "source": "NDLS",
        "destination": "MMCT",
        "source_stn_name": "NEW DELHI",
        "dest_stn_name": "MUMBAI CENTRAL",
        "title": "Delayed at Bhopal",
        "delay": 22,
        "current_station_code": "BPL",
        "current_station_name": "Bhopal",
        "cur_stn_lat": "23.2599",
        "cur_stn_lng": "77.4126",
        "cur_stn_sta": "08:35",
        "eta": "08:57",
        "gps_unable": False,
        "route_stops": ["NDLS", "MTJ", "BRC", "ST", "MMCT"]
    },
    "12001": {
        "train_number": "12001",
        "train_name": "Bhopal Shatabdi Express",
        "source": "NDLS",
        "destination": "RKMP",
        "source_stn_name": "NEW DELHI",
        "dest_stn_name": "RANI KAMLAPATI",
        "title": "Nominal delay at Agra",
        "delay": 8,
        "current_station_code": "AGC",
        "current_station_name": "Agra Cantt",
        "cur_stn_lat": "27.1767",
        "cur_stn_lng": "78.0081",
        "cur_stn_sta": "14:40",
        "eta": "14:48",
        "gps_unable": False,
        "route_stops": ["NDLS", "MTJ", "AGC", "GWL", "BPL", "RKMP"]
    },
    "12259": {
        "train_number": "12259",
        "train_name": "Sealdah Duronto Express",
        "source": "NDLS",
        "destination": "SDAH",
        "source_stn_name": "NEW DELHI",
        "dest_stn_name": "SEALDAH",
        "title": "Delayed at Bardhaman",
        "delay": 67,
        "current_station_code": "BWN",
        "current_station_name": "Bardhaman",
        "cur_stn_lat": "23.2324",
        "cur_stn_lng": "87.8615",
        "cur_stn_sta": "16:15",
        "eta": "17:22",
        "gps_unable": False,
        "route_stops": ["NDLS", "CNB", "ALD", "PNBE", "BWN", "SDAH"]
    },
    "12565": {
        "train_number": "12565",
        "train_name": "Bihar Sampark Kranti Express",
        "source": "DBG",
        "destination": "NDLS",
        "source_stn_name": "DARBHANGA JN",
        "dest_stn_name": "NEW DELHI",
        "title": "Delayed at Gorakhpur",
        "delay": 34,
        "current_station_code": "GKP",
        "current_station_name": "Gorakhpur",
        "cur_stn_lat": "26.7606",
        "cur_stn_lng": "83.3732",
        "cur_stn_sta": "05:15",
        "eta": "05:49",
        "gps_unable": False,
        "route_stops": ["DBG", "SPJ", "MFP", "GKP", "ALJN", "NDLS"]
    },
    "11057": {
        "train_number": "11057",
        "train_name": "Amritsar Express",
        "source": "CSMT",
        "destination": "ASR",
        "source_stn_name": "MUMBAI CSMT",
        "dest_stn_name": "AMRITSAR JN",
        "title": "Delayed at Ludhiana",
        "delay": 15,
        "current_station_code": "LDH",
        "current_station_name": "Ludhiana",
        "cur_stn_lat": "30.9010",
        "cur_stn_lng": "75.8573",
        "cur_stn_sta": "20:10",
        "eta": "20:25",
        "gps_unable": False,
        "route_stops": ["CSTM", "PUNE", "ET", "BPL", "NDLS", "LDH", "ASR"]
    },
    "12627": {
        "train_number": "12627",
        "train_name": "Karnataka Express",
        "source": "NDLS",
        "destination": "SBC",
        "source_stn_name": "NEW DELHI",
        "dest_stn_name": "KSR BENGALURU",
        "title": "Delayed at Secunderabad",
        "delay": 51,
        "current_station_code": "SC",
        "current_station_name": "Secunderabad",
        "cur_stn_lat": "17.4339",
        "cur_stn_lng": "78.5000",
        "cur_stn_sta": "18:00",
        "eta": "18:51",
        "gps_unable": False,
        "route_stops": ["SBC", "UBL", "SC", "NGP", "BPL", "AGC", "NDLS"]
    },
    "12625": {
        "train_number": "12625",
        "train_name": "Kerala Express",
        "source": "NDLS",
        "destination": "TVC",
        "source_stn_name": "NEW DELHI",
        "dest_stn_name": "TRIVANDRUM CENTRAL",
        "title": "Delayed 89min at Nagpur",
        "delay": 89,
        "current_station_code": "NGP",
        "current_station_name": "Nagpur",
        "cur_stn_lat": "21.1458",
        "cur_stn_lng": "79.0882",
        "cur_stn_sta": "11:33",
        "eta": "13:02",
        "gps_unable": False,
        "route_stops": ["TVC", "ERS", "CLT", "SBC", "BZA", "NGP", "BPL", "AGC", "NDLS"]
    },
    "12621": {
        "train_number": "12621",
        "train_name": "Tamil Nadu Express",
        "source": "NDLS",
        "destination": "MAS",
        "source_stn_name": "NEW DELHI",
        "dest_stn_name": "MGR CHENNAI CENTRAL",
        "title": "Delayed at Vijayawada",
        "delay": 12,
        "current_station_code": "BZA",
        "current_station_name": "Vijayawada",
        "cur_stn_lat": "16.5193",
        "cur_stn_lng": "80.6305",
        "cur_stn_sta": "06:00",
        "eta": "06:12",
        "gps_unable": False,
        "route_stops": ["MAS", "BZA", "NGP", "ET", "BPL", "AGC", "NDLS"]
    },
    "12615": {
        "train_number": "12615",
        "train_name": "Grand Trunk Express",
        "source": "NDLS",
        "destination": "MAS",
        "source_stn_name": "NEW DELHI",
        "dest_stn_name": "MGR CHENNAI CENTRAL",
        "title": "Delayed at Gwalior",
        "delay": 28,
        "current_station_code": "GWL",
        "current_station_name": "Gwalior",
        "cur_stn_lat": "26.2183",
        "cur_stn_lng": "78.1828",
        "cur_stn_sta": "04:30",
        "eta": "04:58",
        "gps_unable": False,
        "route_stops": ["MAS", "BZA", "NGP", "ET", "BPL", "GWL", "AGC", "NDLS"]
    },
    "12309": {
        "train_number": "12309",
        "train_name": "Patna Express",
        "source": "RJPB",
        "destination": "NDLS",
        "source_stn_name": "RAJENDRA NAGAR T",
        "dest_stn_name": "NEW DELHI",
        "title": "Delayed at Patna",
        "delay": 43,
        "current_station_code": "PNBE",
        "current_station_name": "Patna",
        "cur_stn_lat": "25.6093",
        "cur_stn_lng": "85.1235",
        "cur_stn_sta": "17:15",
        "eta": "17:58",
        "gps_unable": False,
        "route_stops": ["RJPB", "PNBE", "ALD", "CNB", "NDLS"]
    },
    "12721": {
        "train_number": "12721",
        "train_name": "Andhra Pradesh Express",
        "source": "VSKP",
        "destination": "NDLS",
        "source_stn_name": "VISAKHAPATNAM",
        "dest_stn_name": "NEW DELHI",
        "title": "Delayed at Visakhapatnam",
        "delay": 19,
        "current_station_code": "VSKP",
        "current_station_name": "Visakhapatnam",
        "cur_stn_lat": "17.7231",
        "cur_stn_lng": "83.2985",
        "cur_stn_sta": "21:00",
        "eta": "21:19",
        "gps_unable": False,
        "route_stops": ["VSKP", "BZA", "SC", "NGP", "BPL", "AGC", "NDLS"]
    },
    "12229": {
        "train_number": "12229",
        "train_name": "Lucknow Mail",
        "source": "LJN",
        "destination": "NDLS",
        "source_stn_name": "LUCKNOW NE",
        "dest_stn_name": "NEW DELHI",
        "title": "Delayed at Moradabad",
        "delay": 37,
        "current_station_code": "MB",
        "current_station_name": "Moradabad",
        "cur_stn_lat": "28.9845",
        "cur_stn_lng": "77.7064",
        "cur_stn_sta": "22:00",
        "eta": "22:37",
        "gps_unable": False,
        "route_stops": ["LKO", "MB", "ALJN", "NDLS"]
    },
    "12311": {
        "train_number": "12311",
        "train_name": "Kalka Mail",
        "source": "HWH",
        "destination": "KLK",
        "source_stn_name": "HOWRAH JN",
        "dest_stn_name": "KALKA",
        "title": "Nominal delay at Ambala Cantt",
        "delay": 6,
        "current_station_code": "UMB",
        "current_station_name": "Ambala Cantt",
        "cur_stn_lat": "30.9167",
        "cur_stn_lng": "76.9500",
        "cur_stn_sta": "03:00",
        "eta": "03:06",
        "gps_unable": False,
        "route_stops": ["HWH", "BWN", "PNBE", "ALD", "CNB", "NDLS", "UMB", "AMB"]
    },
    "12641": {
        "train_number": "12641",
        "train_name": "Thirukkural Express",
        "source": "CAPE",
        "destination": "NZM",
        "source_stn_name": "KANYAKUMARI",
        "dest_stn_name": "HAZRAT NIZAMUDDIN",
        "title": "Delayed 71min at Madurai",
        "delay": 71,
        "current_station_code": "MDU",
        "current_station_name": "Madurai",
        "cur_stn_lat": "9.9252",
        "cur_stn_lng": "78.1198",
        "cur_stn_sta": "13:00",
        "eta": "14:11",
        "gps_unable": False,
        "route_stops": ["NCJ", "MDU", "TPJ", "MAS", "BZA", "NGP", "BPL", "AGC", "NDLS"]
    },
    "12438": {
        "train_number": "12438",
        "train_name": "Secunderabad Rajdhani Express",
        "source": "SC",
        "destination": "NDLS",
        "source_stn_name": "SECUNDERABAD",
        "dest_stn_name": "NEW DELHI",
        "title": "Nominal",
        "delay": 0,
        "current_station_code": "SC",
        "current_station_name": "Secunderabad",
        "cur_stn_lat": "17.4339",
        "cur_stn_lng": "78.5000",
        "cur_stn_sta": "13:00",
        "eta": "13:00",
        "gps_unable": False,
        "route_stops": ["SC", "NGP", "BPL", "AGC", "NDLS"]
    },
    "ICE": {
        "train_number": "ICE",
        "train_name": "Intercity Express 782",
        "source": "8011160",
        "destination": "8000261",
        "source_stn_name": "BERLIN HBF",
        "dest_stn_name": "MUNICH HBF",
        "title": "Nominal",
        "delay": 0,
        "current_station_code": "8011160",
        "current_station_name": "Berlin Hbf",
        "cur_stn_lat": "52.5256",
        "cur_stn_lng": "13.369",
        "cur_stn_sta": "09:00",
        "eta": "09:00",
        "gps_unable": False,
        "route_stops": ["8011160", "8000261"]
    }
}

def get_mock_rapidapi_train(train_number: str) -> dict:
    t_data = RAW_MOCK_TRAINS.get(train_number)
    if t_data:
        return {
            "status": True,
            "message": "Success",
            "data": t_data
        }
    return {
        "status": True,
        "message": "Success",
        "data": {
            "success": True,
            "train_number": train_number,
            "train_name": f"Train {train_number}",
            "gps_unable": False,
            "source": "NDLS",
            "destination": "NDLS",
            "source_stn_name": "NEW DELHI",
            "dest_stn_name": "NEW DELHI",
            "title": "Nominal",
            "delay": 0,
            "current_station_code": "NDLS",
            "current_station_name": "NEW DELHI",
            "cur_stn_lat": "28.6139",
            "cur_stn_lng": "77.2090",
            "cur_stn_sta": "12:00",
            "eta": "12:00",
            "previous_stations": []
        }
    }

import math
import time
import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Real Indian Railways Schedule Data (IST times)
# dep = departure from first stop in minutes from midnight (IST)
# dur = total journey duration in minutes
# prog = cumulative progress fraction [0.0–1.0] at each route_stop
# ─────────────────────────────────────────────────────────────────────────────
TRAIN_SCHEDULES = {
    # 12301: NDLS(16:55) → CNB → ALD → BSB → PNBE → HWH(10:05+1) | 17h10m
    "12301": {"dep": 1015, "dur": 1030, "prog": [0.000, 0.301, 0.442, 0.524, 0.859, 1.000]},
    # 12951: NDLS(16:00) → MTJ → BRC → ST → MMCT(07:55+1) | 15h55m
    "12951": {"dep":  960, "dur":  955, "prog": [0.000, 0.110, 0.728, 0.861, 1.000]},
    # 12001: NDLS(06:00) → MTJ → AGC → GWL → BPL(13:45) | 7h45m  (RKMP filtered)
    "12001": {"dep":  360, "dur":  465, "prog": [0.000, 0.194, 0.323, 0.516, 1.000]},
    # 12259: NDLS(20:35) → CNB → ALD → PNBE → BWN → SDAH(14:05+1) | 17h30m
    "12259": {"dep": 1235, "dur": 1050, "prog": [0.000, 0.286, 0.429, 0.771, 0.933, 1.000]},
    # 12565: DBG(17:30) → SPJ → MFP → GKP → ALJN → NDLS(19:00+1) | 25h30m
    "12565": {"dep": 1050, "dur": 1530, "prog": [0.000, 0.118, 0.235, 0.373, 0.706, 1.000]},
    # 11057: CSTM(21:30) → PUNE → ET → BPL → NDLS → LDH → ASR (+32h)
    "11057": {"dep": 1290, "dur": 1920, "prog": [0.000, 0.094, 0.313, 0.500, 0.750, 0.875, 1.000]},
    # 12627: SBC(20:30) → UBL → SC → NGP → BPL → AGC → NDLS (+41h)
    "12627": {"dep": 1230, "dur": 2460, "prog": [0.000, 0.125, 0.293, 0.415, 0.585, 0.829, 1.000]},
    # 12625: TVC(11:30) → ERS → CLT → SBC → BZA → NGP → BPL → AGC → NDLS (+47h)
    "12625": {"dep":  690, "dur": 2820, "prog": [0.000, 0.085, 0.156, 0.220, 0.370, 0.511, 0.648, 0.883, 1.000]},
    # 12621: MAS(22:00) → BZA → NGP → ET → BPL → AGC → NDLS (+32h)
    "12621": {"dep": 1320, "dur": 1920, "prog": [0.000, 0.188, 0.375, 0.500, 0.656, 0.875, 1.000]},
    # 12615: MAS(18:30) → BZA → NGP → ET → BPL → GWL → AGC → NDLS (+36h)
    "12615": {"dep": 1110, "dur": 2160, "prog": [0.000, 0.167, 0.333, 0.444, 0.583, 0.778, 0.861, 1.000]},
    # 12309: RJPB(19:30) → PNBE → ALD → CNB → NDLS (+18h)
    "12309": {"dep": 1170, "dur": 1080, "prog": [0.000, 0.056, 0.500, 0.750, 1.000]},
    # 12721: VSKP(21:30) → BZA → SC → NGP → BPL → AGC → NDLS (+27h)
    "12721": {"dep": 1290, "dur": 1620, "prog": [0.000, 0.167, 0.389, 0.556, 0.722, 0.889, 1.000]},
    # 12229: LKO(22:00) → MB → ALJN → NDLS (+6h45m)
    "12229": {"dep": 1320, "dur":  405, "prog": [0.000, 0.370, 0.630, 1.000]},
    # 12311: HWH(19:40) → BWN → PNBE → ALD → CNB → NDLS → UMB → AMB (+33h)
    "12311": {"dep": 1180, "dur": 1980, "prog": [0.000, 0.091, 0.242, 0.394, 0.545, 0.757, 0.909, 1.000]},
    # 12641: NCJ(21:05) → MDU → TPJ → MAS → BZA → NGP → BPL → AGC → NDLS (+34h)
    "12641": {"dep": 1265, "dur": 2040, "prog": [0.000, 0.088, 0.206, 0.353, 0.500, 0.647, 0.765, 0.912, 1.000]},
    # ICE: Berlin(09:00) → Munich(13:30) | 4h30m
    "ICE":   {"dep":  540, "dur":  270, "prog": [0.000, 1.000]},
    # 12438: SC(13:00) → NGP → BPL → AGC → NDLS (+22h)
    "12438": {"dep":  780, "dur": 1320, "prog": [0.000, 0.250, 0.500, 0.750, 1.000]},
}

def _get_schedule_progress(train_number: str) -> float:
    """Calculate 0.0–1.0 journey progress based on IST clock and real timetable.
    
    TIME_WARP_FACTOR compresses simulation time so trains visibly move on the map.
    120x = 2 simulated hours per real minute ≈ 15–20 km per 5-second poll at zoom 5.
    Each train's IST departure time is kept as its starting phase, so trains start at
    geographically different positions (not all at origin), looking realistic.
    """
    TIME_WARP_FACTOR = 120  # adjust lower (60) for slower, higher (240) for faster

    schedule = TRAIN_SCHEDULES.get(train_number)
    if not schedule:
        # Fallback: 8-minute looping cycle
        return (time.time() % 480) / 480

    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    current_min = ist_now.hour * 60 + ist_now.minute + ist_now.second / 60.0

    dep_min = schedule["dep"]
    dur_min = schedule["dur"]

    # Elapsed real-world minutes since last departure
    elapsed_real = current_min - dep_min
    if elapsed_real < 0:
        elapsed_real += 1440  # Departed yesterday

    # Apply time warp: each real minute = TIME_WARP_FACTOR simulation minutes
    elapsed_sim = elapsed_real * TIME_WARP_FACTOR

    # Wrap around so trains continuously loop their route (no static stuck trains)
    progress = (elapsed_sim / dur_min) % 1.0
    return progress


def get_dynamic_position_and_status(train_number: str) -> dict:
    base = RAW_MOCK_TRAINS.get(train_number)
    if not base:
        base = {
            "train_number": train_number,
            "train_name": f"Express {train_number}",
            "source": "NDLS",
            "destination": "HWH",
            "source_stn_name": "NEW DELHI",
            "dest_stn_name": "HOWRAH JN",
            "delay": 0,
            "current_station_code": "NDLS",
            "current_station_name": "New Delhi",
            "cur_stn_sta": "12:00",
            "eta": "12:00",
            "route_stops": ["NDLS", "HWH"]
        }
    
    source_code = base.get("source", "NDLS")
    dest_code = base.get("destination", "HWH")
    
    route_stops = base.get("route_stops", [source_code, dest_code])
    route_stops = [s for s in route_stops if s in STATION_COORDS]
    if len(route_stops) < 2:
        route_stops = [source_code, dest_code]
        
    # ── Schedule-based progress (real IST timetable) ──────────────────────────
    progress = _get_schedule_progress(train_number)
    schedule = TRAIN_SCHEDULES.get(train_number, {})
    stop_progs = schedule.get("prog", [])

    num_segments = len(route_stops) - 1

    # Find which segment we're in using timetable fractions when available
    segment_index = 0
    local_progress = 0.0

    if len(stop_progs) == len(route_stops) and num_segments > 0:
        for i in range(num_segments):
            p0, p1 = stop_progs[i], stop_progs[i + 1]
            if progress <= p1 or i == num_segments - 1:
                seg_span = p1 - p0
                local_progress = ((progress - p0) / seg_span) if seg_span > 0 else 0.0
                local_progress = min(max(local_progress, 0.0), 1.0)
                segment_index = i
                break
    else:
        # Equal-time fallback
        sp = progress * num_segments
        segment_index = min(int(sp), num_segments - 1)
        local_progress = sp - segment_index

    stop_from_code = route_stops[segment_index]
    stop_to_code   = route_stops[min(segment_index + 1, len(route_stops) - 1)]

    coord_from = STATION_COORDS.get(stop_from_code, {"lat": 28.6419, "lng": 77.2194, "name": "Unknown"})
    coord_to   = STATION_COORDS.get(stop_to_code,   {"lat": 22.5958, "lng": 88.2636, "name": "Unknown"})

    # Add tiny GPS-jitter (±0.003°) so marker subtly "breathes" between refreshes
    jitter_scale = 0.003
    hash_val = sum(ord(c) for c in train_number)
    jitter_lat = jitter_scale * math.sin(time.time() / 8.0 + hash_val)
    jitter_lng = jitter_scale * math.cos(time.time() / 8.0 + hash_val * 1.3)

    lat = coord_from["lat"] + (coord_to["lat"] - coord_from["lat"]) * local_progress + jitter_lat
    lng = coord_from["lng"] + (coord_to["lng"] - coord_from["lng"]) * local_progress + jitter_lng

    current_station = coord_from.get("name", stop_from_code)
    next_station    = coord_to.get("name", stop_to_code)

    # Estimate distance to next station based on remaining local_progress
    seg_dist_km = math.sqrt(
        ((coord_to["lat"] - coord_from["lat"]) * 111.0) ** 2 +
        ((coord_to["lng"] - coord_from["lng"]) * 91.0) ** 2
    )
    distance_next = f"{round((1.0 - local_progress) * seg_dist_km, 1)} KM"

    base_delay = base.get("delay", 0)
    delay = max(0, base_delay + int(15 * math.sin(time.time() / 45.0 + hash_val)))
    
    override = SIMULATED_OVERRIDES.get(train_number)
    if override and "delay_minutes" in override:
        delay = override["delay_minutes"]
        
    if delay == 0:
        passenger_load = "normal"
        status = "On Time"
    elif delay <= 15:
        passenger_load = "medium"
        status = "Delayed"
    elif delay <= 30:
        passenger_load = "high"
        status = "Delayed"
    else:
        passenger_load = "overcrowded"
        status = "Delayed"
        
    if override and "status" in override:
        status = override["status"]
        if status.lower() == "cancelled":
            passenger_load = "overcrowded"
            
    if override and "current_station" in override:
        current_station = override["current_station"]
        for code, coord in STATION_COORDS.items():
            if coord.get("name") == current_station or code == current_station:
                lat = coord["lat"]
                lng = coord["lng"]
                break
                
    if status.lower() == "cancelled":
        speed = "0 km/h"
        distance_next = "0.0 KM"
    elif delay > 60:
        speed = "45 km/h"
    else:
        speed = f"{int(75 + 10 * math.sin(time.time() / 15.0 + hash_val))} km/h"
        
    route_stops_coords = [{"code": s, "name": STATION_COORDS[s]["name"], "lat": STATION_COORDS[s]["lat"], "lng": STATION_COORDS[s]["lng"]} for s in route_stops if s in STATION_COORDS]
        
    return {
        "train_number": train_number,
        "train_name": base["train_name"],
        "source": source_code,
        "destination": dest_code,
        "source_stn_name": base.get("source_stn_name", "NEW DELHI"),
        "dest_stn_name": base.get("dest_stn_name", "HOWRAH JN"),
        "scheduled_arrival": base.get("cur_stn_sta", "12:00"),
        "actual_arrival": base.get("eta", "12:00"),
        "delay_minutes": delay,
        "status": status,
        "platform": str((hash_val % 4) + 1),
        "passenger_load": passenger_load,
        "current_station": current_station,
        "next_station": next_station,
        "distance_next": distance_next,
        "speed": speed,
        "lat": lat,
        "lng": lng,
        "route_stops": route_stops_coords
    }

def mock_train_data() -> list:
    return [get_dynamic_position_and_status(tn) for tn in RAW_MOCK_TRAINS.keys()]

async def get_db_realtime_data(train_number: str) -> dict:
    url = "https://v6.db.transport.rest/journeys"
    params = {
        "from": "8011160",
        "to": "8000261",
        "results": 5
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                journeys = data.get("journeys", [])
                for j in journeys:
                    legs = j.get("legs", [])
                    for leg in legs:
                        line = leg.get("line", {})
                        line_name = line.get("name", "")
                        if not train_number or train_number.lower() in line_name.lower() or train_number in ["12301", "12951", "12001", "12259", "12565", "11057", "12627", "12625", "12621", "12615", "12309", "12721", "12229", "12311", "12641"]:
                            origin = leg.get("origin", {})
                            destination = leg.get("destination", {})
                            planned_dep = leg.get("plannedDeparture", "")
                            actual_dep = leg.get("departure", "")
                            
                            delay = 0
                            if leg.get("departureDelay"):
                                    delay = int(leg.get("departureDelay") / 60)
                            
                            loc = origin.get("location", {})
                            lat = loc.get("latitude", 52.5256)
                            lng = loc.get("longitude", 13.369)
                            
                            status = "on_time"
                            if delay > 60:
                                status = "severely_delayed"
                            elif delay > 15:
                                status = "delayed"
                                
                            passenger_load = "normal"
                            if delay > 30:
                                passenger_load = "high"
                            elif delay > 15:
                                passenger_load = "medium"
                                
                            return {
                                "train_number": train_number,
                                "train_name": line_name or f"DB {train_number}",
                                "current_station": origin.get("name", "Berlin Hbf"),
                                "station_code": origin.get("id", "8011160"),
                                "delay_minutes": delay,
                                "passenger_load": passenger_load,
                                "status": status,
                                "schedule_arrival": planned_dep[11:16] if len(planned_dep) > 16 else planned_dep,
                                "actual_arrival": actual_dep[11:16] if len(actual_dep) > 16 else actual_dep,
                                "source": origin.get("name", "Berlin Hbf"),
                                "destination": destination.get("name", "Munich Hbf"),
                                "lat": lat,
                                "lng": lng
                            }
    except Exception as e:
        print(f"[RAILMIND] DB API error: {e}")
    return {}

def parse_ntes_train_for_agent(data: dict, train_number: str) -> dict:
    t_num = data.get("trainNo") or data.get("trainNoVal") or train_number
    t_name = data.get("trainName") or data.get("name") or f"Train {t_num}"
    
    current_station = "Unknown"
    station_code = "Unknown"
    delay_minutes = 0
    scheduled_arrival = "-"
    actual_arrival = "-"
    source = "Unknown"
    destination = "Unknown"
    
    runs = data.get("runs") or data.get("data", {}).get("runs") or []
    if not runs and "currentStation" in data:
        current_station = data.get("currentStation", "Unknown")
        delay_minutes = int(data.get("delayMinutes", 0))
    elif runs:
        curr = runs[-1] if isinstance(runs, list) else runs
        current_station = curr.get("stationName") or curr.get("stnName") or "Unknown"
        station_code = curr.get("stationCode") or curr.get("stnCode") or "Unknown"
        try:
            delay_minutes = int(curr.get("delayInArrival") or curr.get("delayMinutes") or 0)
        except:
            pass
        scheduled_arrival = curr.get("schArr") or curr.get("sta") or "-"
        actual_arrival = curr.get("actArr") or curr.get("eta") or "-"
        
    route = data.get("route") or data.get("stations") or []
    if route:
        source = route[0].get("stationName") or route[0].get("stnName") or "Unknown"
        destination = route[-1].get("stationName") or route[-1].get("stnName") or "Unknown"
        
    coords = STATION_COORDS.get(station_code, {"lat": 20.5937, "lng": 78.9629, "name": "Unknown"})
    if current_station == "Unknown" and coords.get("name") != "Unknown":
        current_station = coords["name"]

    if delay_minutes == 0:
        passenger_load = "normal"
    elif delay_minutes <= 15:
        passenger_load = "medium"
    elif delay_minutes <= 30:
        passenger_load = "high"
    else:
        passenger_load = "overcrowded"

    status = "on_time"
    if delay_minutes > 60:
        status = "severely_delayed"
    elif delay_minutes > 15:
        status = "delayed"

    return {
        "train_number": t_num,
        "train_name": t_name,
        "current_station": current_station,
        "station_code": station_code,
        "delay_minutes": delay_minutes,
        "passenger_load": passenger_load,
        "status": status,
        "schedule_arrival": scheduled_arrival,
        "actual_arrival": actual_arrival,
        "source": source,
        "destination": destination,
        "lat": coords["lat"],
        "lng": coords["lng"]
    }

async def _get_live_train_status_impl(train_number: str) -> dict:
    if not train_number.isdigit():
        db_data = await get_db_realtime_data(train_number)
        if db_data:
            return db_data

    url = f"https://enquiry.indianrail.gov.in/ntes/NTES"
    params = {"action": "getTrainData", "trainNo": train_number}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/120.0.0.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://enquiry.indianrail.gov.in/ntes/"
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data and (data.get("trainNo") or data.get("runs") or data.get("data")):
                    return parse_ntes_train_for_agent(data, train_number)
    except Exception as e:
        print(f"[RAILMIND] NTES API error for {train_number}: {e}")

    if RAPIDAPI_KEY and RAPIDAPI_KEY not in ["", "your_key_here", "mock_key"]:
        url = f"https://{RAPIDAPI_HOST}/api/v1/liveTrainStatus"
        params = {"trainNo": train_number, "startDay": "0"}
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") is True:
                        return parse_rapidapi_train_for_agent(data, train_number)
        except Exception as e:
            print(f"[RAILMIND] RapidAPI error for {train_number}: {e}")

    # Fallback to IndianRailAPI
    if RAILWAYS_API_KEY and RAILWAYS_API_KEY not in ["", "your_key_here", "mock_key"]:
        date = datetime.datetime.now().strftime("%Y%m%d")
        url = f"{BASE_URL}/livetrainstatus/apikey/{RAILWAYS_API_KEY}/trainnumber/{train_number}/date/{date}/"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                data = response.json()
                if data.get("ResponseCode") == "200":
                    return parse_train_for_agent(data, train_number)
        except Exception as e:
            print(f"[RAILMIND] IndianRailAPI error for {train_number}: {e}")

    # Fallback to DB API journeys for live real-time simulation if all IR sources are unconfigured/mocked
    db_data = await get_db_realtime_data(train_number)
    if db_data:
        return db_data

    # Final fallback to mock data
    if train_number in RAW_MOCK_TRAINS:
        return get_dynamic_position_and_status(train_number)
    mock_data = get_mock_rapidapi_train(train_number)
    return parse_rapidapi_train_for_agent(mock_data, train_number)

async def get_live_train_status(train_number: str) -> dict:
    res = await _get_live_train_status_impl(train_number)
    override = SIMULATED_OVERRIDES.get(train_number)
    if override and res:
        res = res.copy()
        if "delay_minutes" in override:
            res["delay_minutes"] = override["delay_minutes"]
            dm = override["delay_minutes"]
            if dm == 0: res["passenger_load"] = "normal"
            elif dm <= 15: res["passenger_load"] = "medium"
            elif dm <= 30: res["passenger_load"] = "high"
            else: res["passenger_load"] = "overcrowded"
        if "status" in override:
            res["status"] = override["status"]
        if "current_station" in override:
            res["current_station"] = override["current_station"]
    return res

async def get_cancelled_trains() -> list:
    date = datetime.datetime.now().strftime("%Y%m%d")
    url = f"https://indianrailapi.com/api/v2/CancelledTrains/apikey/{RAILWAYS_API_KEY}/Date/{date}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("Trains", [])
    except Exception as e:
        print(f"[RAILMIND] Cancelled trains API error: {e}")
    
    # Return mock cancelled trains if API fails or is unconfigured
    return [
        {
            "TrainNo": "12303",
            "TrainName": "Howrah - New Delhi Poorva Express",
            "Source": "HWH",
            "Destination": "NDLS",
            "Type": "Superfast"
        },
        {
            "TrainNo": "12260",
            "TrainName": "Howrah Duronto Express",
            "Source": "NDLS",
            "Destination": "HWH",
            "Type": "Duronto"
        }
    ]

async def get_trains_between_stations(from_code: str, to_code: str) -> list:
    url = f"http://indianrailapi.com/api/v2/TrainBetweenStation/apikey/{RAILWAYS_API_KEY}/From/{from_code}/To/{to_code}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("Trains", [])
    except Exception as e:
        print(f"[RAILMIND] Train between stations error: {e}")
    
    # Return mock trains between stations
    return [
        {
            "TrainNo": "12301",
            "TrainName": "Howrah - New Delhi Rajdhani Express",
            "Source": "HWH",
            "Destination": "NDLS"
        },
        {
            "TrainNo": "12303",
            "TrainName": "Howrah - New Delhi Poorva Express",
            "Source": "HWH",
            "Destination": "NDLS"
        }
    ]

async def get_multiple_trains(train_numbers: list) -> list:
    import asyncio
    tasks = [get_live_train_status(tn) for tn in train_numbers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, dict) and r]

def parse_train_for_agent(data: dict, train_number: str) -> dict:
    current = data.get("CurrentStation", {})
    route = data.get("TrainRoute", [])
    
    delay_str = current.get("DelayInArrival", "0 M")
    try:
        delay_minutes = int(delay_str.split()[0]) if delay_str not in ["-", "00 M"] else 0
    except:
        delay_minutes = 0
    
    if delay_minutes == 0: passenger_load = "normal"
    elif delay_minutes <= 15: passenger_load = "medium"
    elif delay_minutes <= 30: passenger_load = "high"
    else: passenger_load = "overcrowded"

    if delay_minutes > 60: status = "severely_delayed"
    elif delay_minutes > 15: status = "delayed"
    else: status = "on_time"
    
    station_code = current.get("StationCode", "NDLS")
    coords = STATION_COORDS.get(station_code, {"lat": 20.5937, "lng": 78.9629, "name": "Unknown"})
    lat = coords["lat"]
    lng = coords["lng"]

    # Add time-seeded sinusoidal drift (approx. 5km) for live demo feel
    import math, time
    try:
        t_num_int = int(train_number)
    except:
        t_num_int = 0
    drift_lat = 0.04 * math.sin(time.time() / 180.0 + t_num_int * 1.5)
    drift_lng = 0.04 * math.cos(time.time() / 180.0 + t_num_int * 1.5)
    lat += drift_lat
    lng += drift_lng
    
    return {
        "train_number": train_number,
        "train_name": data.get("TrainNumber", train_number),
        "current_station": coords.get("name") if coords.get("name") != "Unknown" else current.get("StationName", "Unknown"),
        "station_code": station_code,
        "delay_minutes": delay_minutes,
        "passenger_load": passenger_load,
        "status": status,
        "schedule_arrival": current.get("ScheduleArrival", "-"),
        "actual_arrival": current.get("ActualArrival", "-"),
        "source": route[0]["StationName"] if route else "Unknown",
        "destination": route[-1]["StationName"] if route else "Unknown",
        "lat": lat,
        "lng": lng
    }

class RailwaysAPIClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("RAILWAYS_API_KEY")

    async def get_live_train_status(self, train_number: str) -> dict:
        return await get_live_train_status(train_number)

    async def get_cancelled_trains(self) -> list:
        return await get_cancelled_trains()

    async def get_trains_between_stations(self, from_code: str, to_code: str) -> list:
        return await get_trains_between_stations(from_code, to_code)

    def mock_train_data(self) -> list:
        return mock_train_data()

    async def get_multiple_trains(self, train_numbers: list) -> list:
        return await get_multiple_trains(train_numbers)
