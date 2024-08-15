# Your Python code goes here 
from langchain_community.llms import Ollama
import requests
import json
from datetime import datetime, timezone
from tqdm import tqdm

# Initialize the LLM model (ensure you have the correct library and initialization code)
try:
    llm = Ollama(model="llama3")  # Replace with the correct initialization code for your model
except NameError:
    print("Error: LLM model is not initialized. Make sure you have the correct library and initialization code.")
    llm = None  # Handle the case where the LLM model isn't available

NOTION_TOKEN = "secret_eZBYbDJ9NdkoBpCCYfE9SoqLmrE8FmEmtTHdczFVO6v"
DATABASE_ID = "9dce30d22bcc4139bb209d00af7d4fba"
PATCH_URL = "https://api.notion.com/v1/pages/{}"  # URL template for updating pages

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def get_pages(num_pages=None):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    page_size = 100 if num_pages is None else num_pages
    payload = {"page_size": page_size}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return []

    data = response.json()
    results = data.get("results", [])

    while data.get("has_more"):
        payload = {"page_size": page_size, "start_cursor": data.get("next_cursor")}
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"An error occurred during pagination: {e}")
            break

        results.extend(data.get("results", []))

    return results

def parse_notion_data(page):
    try:
        page_id = page["id"]
        props = page["properties"]

        # Debugging: Print the entire properties object to understand structure
        print(f"Page ID: {page_id}")
        print(f"Properties: {json.dumps(props, indent=4)}")

        # Access formula result for URL
        url = props.get("URL", {}).get("title", [{}])[0].get("text", {}).get("content", "No URL")

        # Access formula result for Title
        title_obj = props.get("Title", {}).get("formula", {}).get("string", "No Title")
        title = title_obj if title_obj != "No Title" else "No Title"

        # Access formula result for Published date
        published = props.get("Published", {}).get("date", {}).get("start", "")
        if published:
            published = datetime.fromisoformat(published).astimezone(timezone.utc).isoformat()
        else:
            published = None

        return {"id": page_id, "url": url, "title": title, "published": published}

    except KeyError as e:
        print(f"Key error: {e}")
        return {"id": None, "url": "No URL", "title": "No Title", "published": None}

def analyze_property_with_llm(title, url, published):
    # Ensure that the LLM model is initialized
    if llm is None:
        raise RuntimeError("LLM model is not available.")

    # Example analysis prompt for LLM
    prompt = f"""
    Analyze the following results and provide brief and short feedback for improvement in life using the Master Key System Method (Score: 1-100):
    Title: {title}
    """
    # Invoke the LLM model and return the result
    try:
        analysis = llm.invoke(prompt).strip()
        print(f"LLM Analysis: {analysis}")  # Debug print statement
        return analysis
    except Exception as e:
        print(f"Error during LLM analysis: {e}")
        return "Error during analysis"

def patch_page_with_analysis(page_id, analysis):
    url = PATCH_URL.format(page_id)
    # Truncate the analysis text if it exceeds 2000 characters
    max_length = 2000
    truncated_analysis = analysis[:max_length]

    payload = {
        "properties": {
            "Analyze": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": truncated_analysis
                        }
                    }
                ]
            }
        }
    }

    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Updated page {page_id} with analysis.")
    except requests.exceptions.RequestException as e:
        print(f"Error updating page {page_id}: {e}")
        print(f"Payload sent: {json.dumps(payload, indent=4)}")
        print(f"Response content: {response.content.decode('utf-8')}")



def save_to_json(data, filename='notion_data_with_analysis.json'):
    with open(filename, 'w', encoding='utf8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Data with analysis saved to '{filename}'")

# Main script execution
if __name__ == "__main__":
    pages = get_pages()
    parsed_pages = []

    for page in tqdm(pages, desc="Processing Notion pages"):
        parsed_data = parse_notion_data(page)
        
        # Debugging: Print parsed data to ensure correctness
        print(f"Parsed Data: {parsed_data}")

        if 'title' in parsed_data:
            # Analyze the content with LLM
            analysis = analyze_property_with_llm(parsed_data['title'], parsed_data['url'], parsed_data['published'])
            parsed_data['analysis'] = analysis

            # Patch the page with the LLM analysis
            patch_page_with_analysis(parsed_data['id'], analysis)
        else:
            print(f"Skipping page with ID {parsed_data.get('id', 'Unknown ID')} due to missing 'title'.")

        parsed_pages.append(parsed_data)

    # Save to JSON file
    save_to_json(parsed_pages)
    print(f"Data with analysis saved to 'notion_data_with_analysis.json'")
