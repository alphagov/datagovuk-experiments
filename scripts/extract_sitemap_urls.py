import xml.etree.ElementTree as ET

with open("sitemap_2.xml", "r") as f:
    xml_data = f.read()

# Parse the XML (use ET.parse('sitemap.xml') if loading from a file)
root = ET.fromstring(xml_data)

# Define the namespace map
namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

# Extract all <loc> values
urls = [loc.text for loc in root.findall('.//ns:loc', namespaces)]

with open("urls.txt", "w") as f:
    for url in urls[:750]:
        f.write(url + "\n")
