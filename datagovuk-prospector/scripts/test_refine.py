import time
from prospector import db
from prospector import refine

p = db.get_pages()[100]
url = p[0]
html_content = p[-2]
start = time.time()
response = refine.process_dataset_with_llm(html_content, url)
print(f"Took {time.time() - start}S")
