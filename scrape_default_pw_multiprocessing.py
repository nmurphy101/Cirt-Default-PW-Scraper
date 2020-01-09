'''Script scrapes the cirt website for vendor default passwords and writes them to a file'''
import os # For I/O operations
import sys # For I/O operations
from pathlib import Path # To write to a file
import logging # To log errors/successes/changes/etc if needed
import requests # To download the page
import time # To add a delay between the times the scape runs
import itertools # used for/with multiprocessing
from multiprocessing.dummy import Pool as ThreadPool # To speed up scrapping task
import timeit # For task completion time estimations
from bs4 import BeautifulSoup # To parse what we download


# Logging parameters
logger = logging.getLogger(__name__)
hdlr = logging.FileHandler('scrape_default.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

# Start of logger message
logger.info('''**************************************************
                             *------------- Start of log/Script ---------------
                             **************************************************''')

# Global variable for progress tracking
global_on_vendor = 0
global_tot_vendor = 0

# Global variables for customization
global_sleep_time = 10 # 86400 for 24hr
global_file_name = "default_passwords.txt"

def main():
    # Initilize that the global versions are being used in this scope
    global global_on_vendor, global_tot_vendor, global_sleep_time

    # Initilize the previous list of passwords for use later
    pw_set_previous = None

    # Time list initilization
    time_list = []

    # CHANGE SLEEP TIME TO WHATS NEEDED
    sleep_time = global_sleep_time # 86400 for 24hr

    # Infinite Loop
    while True:
        # Reset these global values to 0 for each loop
        global_tot_vendor = 0
        global_on_vendor = 0

        # Get the main page info/data
        url, headers, soup  = main_soup()

        # Get the list of vendors from the main page
        vendor_list = vendor(url, soup)

        # Efficency timer to estimate completion time
        start = timeit.default_timer()

        # Only estimate after getting data to go off of
        if time_list != []:
            print("  Initilizing Password List: \n   -Estimated time: {:.0f}sec"
                  .format(round(sum(time_list)/len(time_list), 0)))
        else:
            print("  Initilizing Password List:")

        # Find all the default passwords of the vendors found
        pool = ThreadPool() # Multiprocessing to find each vendors passwords faster
        pw_sets_list = pool.starmap(find_password, zip(itertools.repeat(headers),vendor_list))
        pool.close()
        pool.join()
        print() # keeps the processed vendors ratio up in standard output

        # Put everything from all the different "threads" into one set
        pw_set_now = set()
        for pw_set in pw_sets_list:
            for pw in pw_set:
                pw_set_now.add(pw)

        # End of efficency timer to give actual time taken finding passwords
        stop = timeit.default_timer()
        print("   -Time taken: {:.0f}sec".format(stop-start))

        # Add to the time list giving more accurate estimation up to 60 past times
        if len(time_list) >= 60:
            time_list.pop(0)
        time_list.append(stop-start)

        # Check for changes in the gathered passwords from the previous loop
        pw_set_previous = check_change(pw_set_now, pw_set_previous)

        # Delay checking again for "sleep_time" ammount
        sleep(sleep_time)


def main_soup():
    try:
        global global_sleep_time

        print("\n  Initilizing Main Page Soup:")
        # Set the main page url to scrape,
        # https://nl.hideproxy.me/go.php?u=s1B9fqmktUywYN0gG62un0aZj%2BRF%2BQ%3D%3D&b=5&f=norefer
        # http://hideme.be/browse.php?u=https%3A%2F%2Fcirt.net%2Fpasswords&b=28
        url = "https://cirt.net/passwords"
        # Set browser headers
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36"
                   "(KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"}
        # Download the main webpage
        response = requests.get(url, headers=headers)
        # Parse the downloaded page and grab all text
        soup = BeautifulSoup(response.text, "lxml")

        return url, headers, soup

    except Exception as e:
        print("  ERROR: {}".format(repr(e)))
        logger.exception(repr(e))
        sleep_time = global_sleep_time
        print(" Retrying in {}sec".format(sleep_time))
        sleep(sleep_time)
        main()

def vendor(url, soup):
    print("  Initilizing Vendor List:")
    # Initilize empty list of links where the default passwords are
    vendor_list = []
    # Initilize that global version is being used in this scope
    global global_tot_vendor

    # Parse for the links to all the default passwords of the listed vendors
    for link in soup.find_all('a'):
        link_href = link.get('href')
        if "?vendor" in link_href:
            global_tot_vendor += 1
            url.replace("&b=28", '')
            vendor_list.append(url + link_href + '&b=28')

    return vendor_list


def find_password(headers, url):
    # Initilize that global version is being used in this scope
    global global_on_vendor
    global global_tot_vendor

    global_on_vendor += 1
    print("   -Processing: {}/{} Vendors".format(global_on_vendor, global_tot_vendor), end="\r")

    # Initilize empty set of default passwords to prevent duplicates
    pw_set_now = set()

    # Parse for the default passwords of each listed vendor
    response = requests.get(url, headers=headers) # Download the vendor webpage
    soup = BeautifulSoup(response.text, "lxml") # Parse the downloaded vendor page for all text

    for table_row in soup.find_all("tr"): # Grab all table rows
        if table_row.find("td", string="Password"): # Grab all tables witn the Password in it
            pw = str(table_row.td.find_next_sibling("td").string) # Grab out the Passoword
            if pw == "(none)": # Instead of (none) have an empty string be a password
                pw = ' '
            # Add the password to the set
            pw_set_now.add(pw)

    return pw_set_now


def check_change(pw_set_now, pw_set_previous):
    global global_file_name

    print("  Checking For Changes:")
    # Check if the list of passwords have changed
    if pw_set_now != pw_set_previous:
        # Log that a change was found
        print("   -Change In Default Password List Detected")
        logger.info("* Change In Default Password List Detected")

        # Set the current list to be compaired next cycle
        pw_set_previous = pw_set_now

        print("     -Writing Password List To File")
        # Open file to write messages to
        file_name = global_file_name
        default_passwords_file = open(os.path.join(sys.path[0], file_name), "w+")

        # Delete whats currently in the file
        default_passwords_file.truncate()

        # Write the passwords to a file one on each line
        for pw in pw_set_now:
            default_passwords_file.write(pw + "\n")

        print("   -File: {} Created".format(file_name))

        default_passwords_file.close()

        # **ADD EMAIL NOTIFICATION OPTION HERE IF WANTED

        return pw_set_previous

    else:
        # Log that it hasn't changed and wait a day to check again
        print("   -No Change In Default Password List Detected")
        logger.info("* No Change In Default Password List Detected")
        # Set the current list to be compaired next cycle
        pw_set_previous = pw_set_now

        return pw_set_previous


def sleep(sleep_time):
    # Check for changes in 24hr (10sec for testing)
    for sec in range(1, sleep_time+1):
        print("  Sleeping for {}/{}sec".format(sec, sleep_time), end='\r')
        time.sleep(1)
    print("\n")
    print("*"*50)


# Run in command line only
if __name__ == '__main__':
    main()
