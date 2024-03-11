#!/usr/bin/python3

#The DDoSia telegram bot seams simple enougth to monitor live for our self, but to make it opsec takes some more work
#A really simple approach for now it to fetch target data files from circl.lu "A bot witha.name" instead, since they monitor the ddosia-network bot and publish the
#target data files in near real time anyway -  https://witha.name/data/
#
# Put MM webhook info i private file in user home dir and source it

import requests
from lxml import html
from datetime import datetime, timedelta
import os
import re

#CA trust store
os.environ["REQUESTS_CA_BUNDLE"] = '/etc/ssl/certs/ca-bundle.trust.crt'
os.environ["SSL_CERT_FILE"] = '/etc/ssl/certs/ca-bundle.trust.crt'


#Where to fetch the monitor data
url = "https://witha.name/data/"
#Save prevoius index-file
last_index_file = "last_index_page.html"
# Specify the directory where you want to save the files
download_directory = "./downloads/"
#Path to webhook file, need to handle ~
webhook_file_path = os.path.expanduser('~/.secrets/webhook_mattermost_secop')

if not (os.path.isfile(webhook_file_path)):
    print("Missing configuration files")
    exit(1)

# Read the webhook URL from the file
with open(webhook_file_path, 'r') as webhook_file:
    webhook_url = webhook_file.read().strip()


# Function to save the index page content
def save_last_index_page(content):
    with open(last_index_file, 'w', encoding='utf-8') as file:
        file.write(content)

# Function to load the content of the last index page
def load_last_index_page():
    if os.path.exists(last_index_file):
        with open(last_index_file, 'r', encoding='utf-8') as file:
            return file.read()
    else:
        #Return empty dummy, if first time run
        return "<html><body><pre></pre></body></html>"

def file_process():
    # Iterate through each downloaded file
    swedish_domains = []
    organization_domains = []
    print("Processing files")
    for file_name in process_files:
        file_path = os.path.join(download_directory, file_name)

        # Ensure the file is a regular file (not a directory)
        if os.path.isfile(file_path):
            # Read the content of the file
            with open(file_path, 'r') as file:
                file_content = file.read()

                # Get all matching .se domains
                swedish_domains.extend(re.findall('"host": ?"(.*?\.se)"', file_content, flags=re.IGNORECASE))

                # Get matches for organization.se domains
                organization_domains.extend(re.findall('"host": ?"(.*?\.organization\.se)"', file_content, flags=re.IGNORECASE))

        # Remove duplicates and sort the lists
        swedish_domains = sorted(set(swedish_domains))
        organization_domains = sorted(set(organization_domains))

        # Print or use the domains as needed
        if swedish_domains:
            print("SWEDISH DOMAINS:", swedish_domains)
            print_domains= '\n'.join(swedish_domains)
            payload = {
                "username": "DDOSIA Monitor",
                "color": "danger",
                "icon_emoji": "skull",
                "text": "",
                "attachments": [
                    {
                        "color": "#FF7000",
                        "pretext": "You can find more target data details at ["+str(url)+file_name+"]("+str(url)+file_name+") and open [telegram channel](https://t.me/s/noname05716eng)",
                        "title": "Swedish organizations targeted by DDOSIA",
                        "text": str(print_domains)  # Convert the list to a string
                    }
                ]
            }
            # Make the POST request to the webhook URL
            response = requests.post(
                webhook_url,
                headers={'Content-Type': 'application/json'},
                json=payload
            )

        if organization_domains:
            print("ORGANIZATION DOMAINS:", organization_domains)
            print_domains= '\n'.join(organization_domains)
            payload = {
                "username": "DDOSIA Monitor",
                "color": "danger",
                "icon_emoji": "skull",
                "text": "",
                "attachments": [
                    {
                        "color": "#900000",
                        "pretext": "You can find more target data details at ["+str(url)+file_name+"]("+str(url)+file_name+") and open [telegram channel](https://t.me/s/noname05716eng)",
                        "title": "ORGANIZATION targeted by DDOSIA",
                        "text": str(print_domains)  # Convert the list to a string
                    }
                ]
            }
            # Make the POST request to the webhook URL
            response = requests.post(
                webhook_url,
                headers={'Content-Type': 'application/json'},
                json=payload
            )


        if not swedish_domains and not organization_domains:
            print("No interesting domains found")


# Send a GET request to the URL
response = requests.get(url)

# Check if the request was successful (status code 200)
if response.status_code == 200:
    # Parse the HTML content with lxml
    tree = html.fromstring(response.content)

    # Find all the <a> tags within the <pre> tag
    links = tree.xpath('//pre/a[contains(text(), "_DDoSia-target-list-full.json")]')

    # Load the content of the last index page
    last_index_page_content = load_last_index_page()

    # Save the current index page content
    save_last_index_page(response.text)

    # Initialize a list to store newly added links
    new_files = []

    # Iterate through the links and identify newly added links
    for link in links:
        file_name = link.text.strip()

        # Check if the link is newly added by comparing with the last index page content
        if last_index_page_content and file_name not in last_index_page_content:
            new_files.append(file_name)

    # Print or use the newly added links as needed
    if new_files:
        print("Newly added files:", new_files)
        # Add your logic to process the newly added links (replace this comment with your code)

        # Create the directory if it doesn't exist
        os.makedirs(download_directory, exist_ok=True)

        last_day = datetime.today() - timedelta(days=1)
        #Download all new files
        process_files = []
        for file_name in new_files:
            print(f"Downloading {file_name}...")

            file_url = url + file_name
            
            # Download the file using requests
            response = requests.get(file_url)
        
            # Save the file to the specified directory
            with open(os.path.join(download_directory, file_name), 'wb') as file:
                file.write(response.content)
                
            print(f"Downloaded {file_name} to {download_directory}")

            # Extract the date-time part from the filename
            date_time_str = file_name.split('_DDoSia')[0]
            try:
                file_time = datetime.strptime(date_time_str, "%Y-%m-%d_%H-%M-%S")
            except ValueError:
               #Filename has incorrect format, some early files had that, skip and continue
                continue
            #Just process and signal on new files with a timestamp from last 24h
            if  file_time > last_day:
                process_files.append(file_name)
    else:
        print("No newly added files")

    if process_files:
        file_process()

else:
    print(f"Failed to retrieve the content. Status code: {response.status_code}")
