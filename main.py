import json
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta  # this gives the exact date after 6 months
import smtplib
import random
import pytz  # for converting the UTC to my local time i.e, IST accurately
from dotenv import load_dotenv
import os


# Load environment variables from the .env file
load_dotenv()

# ---------- constants ----------------
my_email = os.getenv("EMAIL")
password = os.getenv("PASSWORD")

tequila_apikey = os.getenv("TEQILA_API_KEY")

tequila_api_header = {
    "apikey": tequila_apikey
}

SHEETY_USERNAME = os.getenv("SHEETY_USERNAME")
SHEETY_PROJECT_NAME = os.getenv("SHEETY_PROJECT_NAME")
SHEETY_SHEET_NAME = os.getenv("SHEETY_SHEET_NAME")

is_direct_flight_found = True

# ------------- current date and date after 6 months  from now-------------

today = datetime.now().date()
current_date = today.strftime("%d/%m/%Y")  # 14/08/2023

six_months = relativedelta(months=6)
upto_6_months = (today + six_months).strftime("%d/%m/%Y")

# ----------------------------------------------
# Define the UTC time

def utc_to_ist(given_utc_time):
    utc_time = datetime.strptime(given_utc_time, "%Y-%m-%dT%H:%M:%S.%fZ")

    # Convert to IST
    utc_time = pytz.utc.localize(utc_time)
    ist_time = utc_time.astimezone(pytz.timezone("Asia/Kolkata"))

utc_to_ist("2023-09-13T10:05:00.000Z")

# -----------------------------------------------------------


def send_otp_and_verify(f_name, l_name, email):
    """ Send OTP to the email provided and then verifies it ."""

    random_list = [str(random.randint(0, 10)) for _ in range(6)]
    random_otp = int(''.join(random_list))

    with smtplib.SMTP("smtp.office365.com", port=587) as connection:
        connection.starttls()
        connection.login(user=my_email, password=password)
        connection.sendmail(from_addr=my_email, to_addrs=email,
                            msg=f"Subject: Dear {f_name} {l_name}! We're glad to have you on board. 🛩️. Just one step to go. \n\n\n"
                                f" Please confirm your email account by entering the OTP below 👇 \n\n Here is the OTP that you requested for: \n\n {random_otp} \n "
                                f"Don't share this OTP with anyone else 🔐.\n Thanks \n\n If you received this email by mistake, then, please ignore it. You won't be added until your OTP is verified.".encode('utf-8'))
    try_times = 0
    no_error = True
    while no_error and try_times < 6:
        try:
            match_otp = int(input("Please type the OTP that you received on your email: "))

        except ValueError:
            print("Please Only type NUMBERS. 🔢")
        else:
            if match_otp == random_otp:
                no_error = False
                # Json data format
                new_data = {
                    f_name: {
                        "last_name": l_name,
                        "email": email
                    }
                }
                try:
                    with open("customer_data.json", mode="r") as data_file:
                        customer_data = json.load(data_file)
                except json.JSONDecodeError:
                    with open("customer_data.json", mode="w") as data_file:
                        json.dump(new_data, data_file, indent=4)
                else:
                    customer_data.update(new_data)
                    with open("customer_data.json", mode="w") as database:
                        json.dump(customer_data, database, indent=4)

                    print(
                        f"Congratulations! dear {f_name} {l_name}! 🍾. You're successfully subscribed to the Cocu's flight club 🛩️.\n Let's roam around the world! 🍃")
                    exit()
            else:

                try_times += 1
                print(try_times)
                if try_times > 5:
                    print(" \n Maximum tries reached! Please try again later or start again! \n")
                else:
                    print(
                        "\n That's not the correct OTP ❌ \n Tips: Try removing any spaces \n or better type it yourself, instead of copy-pasting \n")
                continue

# ---------------------------------------------------


def add_new_customers():
    """ This function adds a new customer to our database, by asking their details and verifying them"""
    customer_f_name = input("What is your first name?: ")
    l_name = input("what is your last name?: ")
    email = input("what is your email?: ")

    is_email = True
    while is_email:
        type_again_email = input("Please type your email again: ")
        if email == type_again_email:
            is_email = False

            # How to prevent adding the same email twice?
            print(" \n Please hold on! An OTP will be sent to your email for verification 🚀 ")
            print()
            send_otp_and_verify(customer_f_name, l_name, email)
        else:
            print(" \n Email doesn't match. ❌")
            continue

add_new_customers() # -> this function helps in adding new customers locally in a file.json

# ---------------------------------------------------


def find_iata_code(city):  # Paris -> PAR
    """ Finds the IATA codes for the cities mentioned in the Google sheets using Tequila api"""
    tequila_params = {
        "term": city
    }
    answer = requests.get(url="https://api.tequila.kiwi.com/locations/query", params=tequila_params,
                          headers=tequila_api_header)
    data = answer.json()
    iata_code = data["locations"][0]["code"]
    return iata_code

# --------------------------------------------------


def update_iata_code(name_of_city, town_id):
    """ Once, it gets hold of the id of the row of sheets , then updates it with the IATA codes of the city"""
    iata_params = {
        "price": {
            "iataCode": find_iata_code(name_of_city)
        }
    }
    # update the sheets
    response = requests.put(
        url=f"https://api.sheety.co/{SHEETY_USERNAME}/{SHEETY_PROJECT_NAME}/{SHEETY_SHEET_NAME}/{town_id}",
        json=iata_params)
    print(response.json())

# -------------------------------------------


def take_data_send_email(data_list, town, flight_price):
    """ When flight is FOUND, only then this code works, by grabbing particular data received by API, also sends email
    to all the customers emails using json. load to read the data"""
    stopover_cities = []

    fly_from = data_list["flyFrom"]  # airport codes
    fly_to = data_list["flyTo"]
    city_from = data_list["cityFrom"]  # city names
    city_to = data_list["cityTo"]
    price = data_list["price"]  # including return price
    total_nights_to_stay = data_list["nightsInDest"]  # for eg:  18 nights in NYC

    route_list = len(data_list["route"])  # list    # dates in UTC
    utc_departure = (data_list["route"][0]["utc_departure"]).split("T")[0]
    utc_arrival = (data_list["route"][route_list - 1]["utc_arrival"]).split("T")[0]
    link = data_list["deep_link"]
    # ------------ sends email ------------------

    via = ""
    if price < flight_price:
        if route_list > 2:  # LON->PAR , PAR->LON
            # find stopovers
            via = "via"

            for n in range(route_list):
                stopover = data_list["route"][n]["cityTo"]
                stopover_cities.append(stopover)
            if city_from or city_to in stopover_cities:
                stopover_cities.remove(city_to)
                stopover_cities.remove(city_from)

            print(', '.join(stopover_cities))

        def direct_flight_or_not():
            if route_list > 2:
                return f"You'll have total of {len(stopover_cities)} stopovers {via} {', '.join(stopover_cities)}"
            else:
                return "It will be a Direct flight ✈️"

        with open("customer_data.json", mode="r") as customer_file:
            customer_info = json.load(customer_file)
            print(customer_info)
            print(type(customer_info))

        for key, value in customer_info.items():
            name = key
            l_name = value["last_name"]
            customer_email = value["email"]
            print(f"sending email to: {name} 👉 {customer_email}")
            # total_nights_to_stay = None
            with smtplib.SMTP("smtp.office365.com", port=587) as connection:
                connection.starttls()
                connection.login(user=my_email, password=password)
                connection.sendmail(from_addr=my_email, to_addrs=customer_email,
                                    msg=f"Subject: Low price alert for {city_to} 🛩️\n\n  Hello dear {name} {l_name} ! \n\n Only   ₹ {price}  to fly from "
                                        f"{city_from}-{fly_from} to {city_to}-{fly_to}, from {utc_departure}"
                                        f" to {utc_arrival} , total {total_nights_to_stay} nights to enjoy in "
                                        f"{city_to}. {direct_flight_or_not()}.\n\n Here is the link 👉 {link}".encode('utf-8'))

        print(f"flight FOUND for {city_to}\n message sent ✅")
        stopover_cities = []
    else:
        cities_with_no_direct_flights.append({
            town: flight_price
        })


# ------------------------------------------------------


def flight_search_params(town, flight_price, max_stop_overs):
    """ This is what we send into the Tequila API to search the flights for us as we want"""
    search_params = {
        "fly_from": "PAT",  # my location # -> london
        "fly_to": town,
        "curr": "INR",
        "date_from": current_date,  # current date
        "date-to": upto_6_months,  # up to 6 months
        "price_to": flight_price,
        "limit": "1",
        "nights_in_dst_from": 7,
        "nights_in_dst_to": 28,
        "max_stopovers": max_stop_overs,
    }

    return search_params

# ------------------------------------------------------


cities_with_no_direct_flights = []
flight_found = False

# 1st search for DIRECT flights, if not found, then check for CONNECTING flights, and if not found, then let it go.

def search_flight(town, flight_price, max_stop_overs):
    """
    This function fills the flight_search_params data into the API and waits for the response., based on whether it got
    empty list or not, appends that city's IATA code to the cities_with_no_direct_flights.
    :param town: IATA Code of city
    :param flight_price: Lowest price mentioned in Google sheets for each city
    :param max_stop_overs: set to 0, for direct flights ONLY
    """
    data = requests.get(url="https://api.tequila.kiwi.com/v2/search",
                        params=flight_search_params(town, flight_price, max_stop_overs),
                        headers=tequila_api_header)
    try:
        city = data.json()["data"][0]["cityTo"]

        print()
        print(f"searching for flights for {city} for max stop over is {max_stop_overs} 🪶✈️ ")
        print()
        data_list = data.json()["data"][0]
        print(data_list)
        if max_stop_overs >= 1 and data_list != 0:
            global flight_found
            flight_found = True
    except IndexError:  # when data_list returns empty
        print(f"No flights found for {town}  ❌")
        cities_with_no_direct_flights.append({
            town: flight_price
        })
    except KeyError:  # cities with no airports
        print(f"This location {town}, doesn't exist on map. No location to fly to.")
    else:
        take_data_send_email(data_list, town, flight_price)


# ----------------- MAIN function -> Get google sheets and search flights-----------

# result = requests.get(url=f"https://api.sheety.co/{SHEETY_USERNAME}/{SHEETY_PROJECT_NAME}/{SHEETY_SHEET_NAME}")
# cities_list = result.json()["prices"]

# for i in range(len(cities_list)):
#     city_id = cities_list[i]["id"]
#     city_name = cities_list[i]["city"]
#     lowest_price = cities_list[i]["lowestPrice"]
#     iata_code = cities_list[i]["iataCode"]
#     print(city_name)

#     search_flight(iata_code, lowest_price, 0)  # try direct flight

# ---------------------------------------------------


def check_connecting_flights():
    """ It loops through each city in the "cities_with_no_direct_flights" list and tries to find the flight
     for as long as max 10 stopovers starting from 1."""

    global flight_found, cities_with_no_direct_flights
    for dictionary in cities_with_no_direct_flights:
        print()
        print(f"cities_with_no_flight: {cities_with_no_direct_flights}")
        print("NOW LOOKING FOR CONNECTING FLIGHTS")
        print()
        for city_code, flight_cost in dictionary.items():  # to get hold of both keys and values
            town_code = city_code
            minimum_price = flight_cost

            max_stop_over = 0
            while max_stop_over < 6 and not flight_found and len(cities_with_no_direct_flights) != 0:
                max_stop_over += 1
                search_flight(town_code, minimum_price, max_stop_over)
                print(f"MAX_STOP_OVER 👉 {max_stop_over}")

            flight_found = False
            new_city_list = [city for city in cities_with_no_direct_flights if town_code not in city]

            cities_with_no_direct_flights = new_city_list
            print(f"cities_with_no_flight: {cities_with_no_direct_flights}")

            if len(cities_with_no_direct_flights) == 0:
                exit()


if len(cities_with_no_direct_flights) != 0:
    check_connecting_flights()
