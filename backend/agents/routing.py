import heapq

# Station Name to Code mapping
STATION_NAME_TO_CODE = {
    "New Delhi": "NDLS",
    "Delhi Junction": "DLI",
    "Kanpur Central": "CNB",
    "Lucknow": "LKO",
    "Prayagraj": "ALD",
    "Allahabad": "ALD",
    "Varanasi": "BSB",
    "Gorakhpur": "GKP",
    "Agra Cantt": "AGC",
    "Mathura": "MTJ",
    "Aligarh": "ALJN",
    "Moradabad": "MB",
    "Saharanpur": "SRE",
    "Ambala": "AMB",
    "Amritsar": "ASR",
    "Ludhiana": "LDH",
    "Ambala Cantt": "UMB",
    "Haridwar": "HW",
    "Dehradun": "DDN",
    "Patna": "PNBE",
    "Rajendra Nagar": "RJPB",
    "Bhagalpur": "BGP",
    "Muzaffarpur": "MFP",
    "Darbhanga": "DBG",
    "Samastipur": "SPJ",
    "Dhanbad": "DHN",
    "Jasidih": "JSME",
    "Ranchi": "RNC",
    "Howrah": "HWH",
    "Sealdah": "SDAH",
    "Kolkata": "KOAA",
    "Bandel": "BDC",
    "Bardhaman": "BWN",
    "Kharagpur": "KGP",
    "Mumbai CST": "CSTM",
    "Mumbai Central": "BCT",
    "Lokmanya Tilak": "LTT",
    "Pune": "PUNE",
    "Nagpur": "NGP",
    "Aurangabad": "AWB",
    "Nanded": "NED",
    "Solapur": "SUR",
    "Bangalore City": "SBC",
    "Yesvantpur": "YPR",
    "Hubli": "UBL",
    "Mysuru": "MYS",
    "Chennai Central": "MAS",
    "Chennai Egmore": "MS",
    "Tiruchirappalli": "TPJ",
    "Madurai": "MDU",
    "Coimbatore": "CBE",
    "Nagercoil": "NCJ",
    "Thiruvananthapuram": "TVC",
    "Ernakulam": "ERS",
    "Kozhikode": "CLT",
    "Shoranur": "SRR",
    "Secunderabad": "SC",
    "Hyderabad": "HYB",
    "Vijayawada": "BZA",
    "Visakhapatnam": "VSKP",
    "Guntur": "GNT",
    "Ahmedabad": "ADI",
    "Vadodara": "BRC",
    "Surat": "ST",
    "Rajkot": "RJT",
    "Bhopal": "BPL",
    "Jabalpur": "JBP",
    "Gwalior": "GWL",
    "Indore": "INDB",
    "Itarsi": "ET",
    "Jaipur": "JP",
    "Ajmer": "AII",
    "Jodhpur": "JU",
    "Bikaner": "BKN",
    "Udaipur": "UDZ",
    "Bhubaneswar": "BBS",
    "Cuttack": "CTC",
    "Puri": "PURI",
    "Guwahati": "GHY",
    "Dibrugarh": "DBRG"
}

# Major Indian railway network graph (station codes)
# Weights represent travel time in minutes
TRACK_GRAPH = {
    # North Mainline & Eastern Corridor
    "NDLS": {"ALJN": 120, "MTJ": 90, "UMB": 180, "SRE": 180, "LKO": 240, "DLI": 15},
    "DLI": {"NDLS": 15, "UMB": 170, "MB": 120},
    "ALJN": {"NDLS": 120, "CNB": 180, "MTJ": 90, "LKO": 150, "MB": 120},
    "CNB": {"ALJN": 180, "ALD": 120, "LKO": 90, "GWL": 180},
    "LKO": {"CNB": 90, "ALD": 120, "BSB": 160, "NDLS": 240, "ALJN": 150, "GKP": 180, "MB": 200},
    "MB": {"DLI": 120, "ALJN": 120, "LKO": 200, "SRE": 120},
    "GKP": {"LKO": 180, "SPJ": 180, "MFP": 180, "BSB": 150},
    "ALD": {"CNB": 120, "BSB": 100, "LKO": 120, "JBP": 240, "MGS": 90},
    "MGS": {"ALD": 90, "BSB": 45, "PNBE": 120, "GAYA": 120},
    "BSB": {"ALD": 100, "PNBE": 150, "LKO": 160, "MGS": 45, "GKP": 150},
    "PNBE": {"BSB": 150, "JSME": 180, "RJPB": 10, "BGP": 150, "MFP": 90},
    "RJPB": {"PNBE": 10},
    "BGP": {"PNBE": 150, "JSME": 120},
    "MFP": {"PNBE": 90, "DBG": 90, "SPJ": 60, "GKP": 180},
    "DBG": {"MFP": 90, "SPJ": 45},
    "SPJ": {"DBG": 45, "MFP": 60, "BGP": 120, "GKP": 180},
    "JSME": {"PNBE": 180, "DHN": 120, "BGP": 120},
    "DHN": {"JSME": 120, "BWN": 120, "RNC": 120},
    "RNC": {"DHN": 120, "JSME": 180},
    "BWN": {"DHN": 120, "HWH": 90, "SDAH": 90, "BDC": 45},
    "BDC": {"BWN": 45, "HWH": 45},
    "HWH": {"BWN": 90, "KGP": 120, "BDC": 45, "KOAA": 20, "SDAH": 20},
    "SDAH": {"BWN": 90, "HWH": 20, "KOAA": 15},
    "KOAA": {"HWH": 20, "SDAH": 15},
    
    # Central & Western Trunk Lines
    "MTJ": {"NDLS": 90, "ALJN": 90, "AGC": 45, "JP": 150},
    "AGC": {"MTJ": 45, "GWL": 90, "JP": 180},
    "GWL": {"AGC": 90, "VGLJ": 120, "CNB": 180},
    "VGLJ": {"GWL": 120, "BPL": 180},
    "BPL": {"VGLJ": 180, "NGP": 240, "JBP": 180, "ET": 90, "INDB": 150},
    "ET": {"BPL": 90, "NGP": 180, "JBP": 180, "CSTM": 360},
    "INDB": {"BPL": 150, "BRC": 240},
    "JBP": {"BPL": 180, "ALD": 240, "NGP": 180, "ET": 180},
    "NGP": {"BPL": 240, "BZA": 360, "JBP": 180, "ET": 180, "CSTM": 360, "SC": 300},
    
    # Western Railway Corridor
    "BCT": {"BRC": 240, "PUNE": 180, "ST": 180, "CSTM": 20, "LTT": 30},
    "CSTM": {"BCT": 20, "LTT": 20, "PUNE": 180, "ET": 360, "NGP": 360},
    "LTT": {"CSTM": 20, "BCT": 30, "PUNE": 180},
    "BRC": {"BCT": 240, "ST": 120, "ADI": 90, "INDB": 240},
    "ST": {"BCT": 180, "BRC": 120, "ADI": 180},
    "ADI": {"ST": 180, "BRC": 90, "RJT": 180, "JP": 300},
    "RJT": {"ADI": 180},
    
    # Southern Railway Corridor
    "BZA": {"NGP": 360, "MAS": 300, "VSKP": 300, "SC": 240, "GNT": 45},
    "GNT": {"BZA": 45, "SC": 210},
    "SC": {"NGP": 300, "BZA": 240, "GNT": 210, "HYB": 15, "SBC": 360},
    "HYB": {"SC": 15},
    "MAS": {"BZA": 300, "MS": 20, "SBC": 240},
    "MS": {"MAS": 20, "SBC": 240, "TPJ": 240},
    "TPJ": {"MS": 240, "MDU": 120, "CBE": 180},
    "MDU": {"TPJ": 120, "NCJ": 180},
    "NCJ": {"MDU": 180, "TVC": 60},
    "TVC": {"NCJ": 60, "ERS": 180},
    "ERS": {"TVC": 180, "SRR": 90},
    "SRR": {"ERS": 90, "CLT": 60, "CBE": 90},
    "CLT": {"SRR": 60},
    "CBE": {"TPJ": 180, "SRR": 90, "SBC": 300},
    
    # South-Western Railway
    "PUNE": {"BCT": 180, "CSTM": 180, "SUR": 240},
    "SUR": {"PUNE": 240, "UBL": 300},
    "UBL": {"SUR": 300, "SBC": 360},
    "SBC": {"UBL": 360, "MS": 240, "YPR": 30, "MYS": 120, "CBE": 300, "SC": 360},
    "YPR": {"SBC": 30},
    "MYS": {"SBC": 120},
    
    # East Coast & Northeast
    "KGP": {"HWH": 120, "CTC": 180},
    "CTC": {"KGP": 180, "BBS": 30},
    "BBS": {"CTC": 30, "VSKP": 360, "PURI": 60},
    "PURI": {"BBS": 60},
    "VSKP": {"BBS": 360, "BZA": 300},
    "GHY": {"DBRG": 360, "HWH": 480},
    "DBRG": {"GHY": 360},
    
    # Northern Mainline
    "ASR": {"LDH": 120},
    "LDH": {"ASR": 120, "UMB": 120},
    "UMB": {"LDH": 120, "NDLS": 180, "DLI": 170, "AMB": 15},
    "AMB": {"UMB": 15},
    "SRE": {"NDLS": 180, "MB": 120, "HW": 60},
    "HW": {"SRE": 60, "DDN": 90},
    "DDN": {"HW": 90},
    
    # Rajasthan Network
    "JP": {"MTJ": 150, "AGC": 180, "ADI": 300, "AII": 120},
    "AII": {"JP": 120, "JU": 150, "UDZ": 180},
    "JU": {"AII": 150, "BKN": 180},
    "BKN": {"JU": 180},
    "UDZ": {"AII": 180}
}

def resolve_code(station: str) -> str:
    """
    Resolves an input station name or code to its standard code.
    """
    if not station:
        return ""
    station_clean = station.strip()
    if station_clean in TRACK_GRAPH:
        return station_clean
    # Try direct name to code matching
    for name, code in STATION_NAME_TO_CODE.items():
        if name.lower() == station_clean.lower():
            return code
    # Try fuzzy name matching
    for name, code in STATION_NAME_TO_CODE.items():
        if station_clean.lower() in name.lower() or name.lower() in station_clean.lower():
            return code
    return station_clean

def dijkstra_route_discovery(start: str, target: str, blocked_station: str = None) -> dict:
    """
    Dijkstra shortest path algorithm. Optional blocked_station parameter will 
    exclude transitions to that station to find detours.
    """
    start_code = resolve_code(start)
    target_code = resolve_code(target)
    blocked_code = resolve_code(blocked_station) if blocked_station else None
    
    if start_code not in TRACK_GRAPH or target_code not in TRACK_GRAPH:
         return {
             "route": [], 
             "cost": -1, 
             "status": f"No graph data for codes: {start_code} / {target_code}"
         }

    distances = {node: float('infinity') for node in TRACK_GRAPH}
    distances[start_code] = 0
    pq = [(0, start_code)]
    previous = {node: None for node in TRACK_GRAPH}

    while pq:
        current_dist, current_node = heapq.heappop(pq)

        if current_node == target_code:
            break

        if current_dist > distances[current_node]:
            continue

        for neighbor, weight in TRACK_GRAPH[current_node].items():
            # Bypass blocked station
            if blocked_code and neighbor == blocked_code:
                continue

            # Some adjacency entries name a station that has no node of its own
            # in the graph. Indexing `distances` with one raised a KeyError that
            # propagated out of the reasoning node and discarded a completed
            # assessment, so a dangling edge is skipped instead.
            if neighbor not in distances:
                continue


            distance = current_dist + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous[neighbor] = current_node
                heapq.heappush(pq, (distance, neighbor))

    route = []
    curr = target_code
    while curr is not None:
        route.append(curr)
        curr = previous[curr]
    route.reverse()

    if len(route) == 1 and start_code != target_code:
        return {"route": [], "cost": -1, "status": "No path found"}

    return {"route": route, "cost": distances[target_code], "status": "Success"}
