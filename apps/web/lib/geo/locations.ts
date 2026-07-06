// Country + city suggestions for enquiry/project location fields.
// Rendered as datalist options: users pick from the list or type a value that
// isn't listed, so the long tail of cities is never blocked.

export const CITIES_BY_COUNTRY: Record<string, string[]> = {
  India: [
    "Mumbai", "Navi Mumbai", "Thane", "Pune", "Nagpur", "Nashik", "Aurangabad",
    "Delhi", "New Delhi", "Noida", "Greater Noida", "Ghaziabad", "Faridabad", "Gurugram",
    "Bengaluru", "Mysuru", "Mangaluru", "Hubli",
    "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Hosur",
    "Hyderabad", "Secunderabad", "Visakhapatnam", "Vijayawada",
    "Kolkata", "Howrah", "Durgapur", "Haldia",
    "Ahmedabad", "Gandhinagar", "Surat", "Vadodara", "Rajkot", "Bharuch", "Ankleshwar", "Jamnagar", "Dahej", "Hazira",
    "Jaipur", "Jodhpur", "Kota", "Udaipur",
    "Lucknow", "Kanpur", "Varanasi", "Prayagraj",
    "Bhopal", "Indore", "Jabalpur", "Gwalior",
    "Chandigarh", "Ludhiana", "Amritsar", "Jalandhar",
    "Kochi", "Ernakulam", "Thiruvananthapuram", "Kozhikode",
    "Bhubaneswar", "Cuttack", "Rourkela", "Paradip", "Angul",
    "Patna", "Ranchi", "Jamshedpur", "Dhanbad",
    "Raipur", "Bhilai", "Bilaspur",
    "Guwahati", "Dibrugarh",
    "Dehradun", "Haridwar", "Rudrapur",
    "Vijayanagar", "Ballari", "Belagavi",
    "Panaji", "Vasco da Gama",
  ],
  "United Arab Emirates": ["Abu Dhabi", "Dubai", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah", "Jebel Ali", "Ruwais", "Musaffah"],
  "Saudi Arabia": ["Riyadh", "Jeddah", "Dammam", "Al Khobar", "Dhahran", "Jubail", "Yanbu", "Mecca", "Medina", "Ras Tanura"],
  Qatar: ["Doha", "Al Wakrah", "Ras Laffan", "Mesaieed", "Al Khor"],
  Oman: ["Muscat", "Sohar", "Salalah", "Sur", "Duqm", "Nizwa"],
  Kuwait: ["Kuwait City", "Ahmadi", "Hawalli", "Jahra", "Shuaiba"],
  Bahrain: ["Manama", "Riffa", "Muharraq", "Sitra", "Hidd"],
  Iraq: ["Baghdad", "Basra", "Erbil", "Kirkuk", "Mosul"],
  Iran: ["Tehran", "Isfahan", "Tabriz", "Shiraz", "Bandar Abbas", "Ahvaz"],
  Egypt: ["Cairo", "Alexandria", "Giza", "Suez", "Port Said", "Damietta"],
  Nigeria: ["Lagos", "Abuja", "Port Harcourt", "Kano", "Warri"],
  "South Africa": ["Johannesburg", "Cape Town", "Durban", "Pretoria", "Port Elizabeth", "Sasolburg"],
  "United States": ["Houston", "New York", "Los Angeles", "Chicago", "Dallas", "Baton Rouge", "Beaumont", "Tulsa", "New Orleans", "Pittsburgh"],
  Canada: ["Toronto", "Calgary", "Edmonton", "Vancouver", "Montreal", "Sarnia", "Fort McMurray"],
  Brazil: ["Sao Paulo", "Rio de Janeiro", "Salvador", "Camacari", "Belo Horizonte"],
  "United Kingdom": ["London", "Manchester", "Birmingham", "Aberdeen", "Middlesbrough", "Hull", "Glasgow"],
  Germany: ["Frankfurt", "Hamburg", "Munich", "Cologne", "Ludwigshafen", "Leverkusen", "Dusseldorf"],
  France: ["Paris", "Lyon", "Marseille", "Le Havre", "Lille", "Fos-sur-Mer"],
  Italy: ["Milan", "Rome", "Turin", "Genoa", "Venice", "Ravenna"],
  Netherlands: ["Rotterdam", "Amsterdam", "The Hague", "Eindhoven", "Geleen"],
  Spain: ["Madrid", "Barcelona", "Valencia", "Bilbao", "Tarragona", "Huelva"],
  Russia: ["Moscow", "Saint Petersburg", "Kazan", "Nizhnekamsk", "Omsk", "Ufa"],
  China: ["Shanghai", "Beijing", "Guangzhou", "Shenzhen", "Ningbo", "Dalian", "Nanjing", "Qingdao"],
  Japan: ["Tokyo", "Osaka", "Yokohama", "Nagoya", "Kobe", "Chiba", "Kawasaki"],
  "South Korea": ["Seoul", "Busan", "Ulsan", "Incheon", "Yeosu", "Daejeon"],
  Singapore: ["Singapore", "Jurong Island"],
  Malaysia: ["Kuala Lumpur", "Johor Bahru", "Pasir Gudang", "Kerteh", "Bintulu", "Penang"],
  Indonesia: ["Jakarta", "Surabaya", "Cilegon", "Bontang", "Balikpapan", "Medan"],
  Thailand: ["Bangkok", "Map Ta Phut", "Rayong", "Chonburi", "Laem Chabang"],
  Vietnam: ["Ho Chi Minh City", "Hanoi", "Vung Tau", "Dung Quat", "Hai Phong"],
  Bangladesh: ["Dhaka", "Chattogram", "Khulna"],
  "Sri Lanka": ["Colombo", "Hambantota"],
  Australia: ["Perth", "Melbourne", "Sydney", "Brisbane", "Gladstone", "Karratha"],
  Turkey: ["Istanbul", "Ankara", "Izmir", "Kocaeli", "Aliaga"],
  Kazakhstan: ["Almaty", "Astana", "Atyrau", "Aktau"],
  Azerbaijan: ["Baku", "Sumqayit"],
};

// A broad country list (name only) for the country dropdown. Countries with a
// curated city list appear in CITIES_BY_COUNTRY above.
export const COUNTRIES: string[] = [
  "Algeria", "Angola", "Argentina", "Australia", "Austria", "Azerbaijan", "Bahrain",
  "Bangladesh", "Belgium", "Brazil", "Brunei", "Canada", "Chile", "China", "Colombia",
  "Denmark", "Egypt", "Finland", "France", "Germany", "Ghana", "Greece", "India",
  "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Japan", "Jordan",
  "Kazakhstan", "Kenya", "Kuwait", "Libya", "Malaysia", "Mexico", "Morocco",
  "Mozambique", "Myanmar", "Netherlands", "New Zealand", "Nigeria", "Norway", "Oman",
  "Pakistan", "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia",
  "Saudi Arabia", "Singapore", "South Africa", "South Korea", "Spain", "Sri Lanka",
  "Sweden", "Switzerland", "Taiwan", "Tanzania", "Thailand", "Tunisia", "Turkey",
  "Turkmenistan", "Ukraine", "United Arab Emirates", "United Kingdom", "United States",
  "Uzbekistan", "Vietnam",
];

export function citiesForCountry(country: string | undefined | null): string[] {
  if (!country) return [];
  return CITIES_BY_COUNTRY[country.trim()] ?? [];
}
