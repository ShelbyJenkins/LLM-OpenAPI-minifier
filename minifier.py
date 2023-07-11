import json
import os
import tiktoken
from collections import defaultdict
import string
import re
import shutil
from urllib.parse import urlparse

tokenizer = tiktoken.encoding_for_model("text-embedding-ada-002")

output_directory = 'minified_openAPI_specs'

# input_filepath = 'LLM-OpenAPI-minifier/input_openAPI_specs/tatum'
# api_url_format = 'https://apidoc.tatum.io/tag/{tag}#operation/{operationId}'

input_filepath = 'LLM-OpenAPI-minifier/input_openAPI_specs/stackpath'
api_url_format = 'https://stackpath.dev/reference/{operationId}'

# input_filepath = 'input_openAPI_specs/weather_dot_gov_swagger.json'
# api_url_format = 'https://www.weather.gov/documentation/services-web-api#/default/{operationId}'

# By default it creates a document for each endpoint

# Create "balanced chunks" of documents consisting of multiple endpoints around the size of token_count_goal
balanced_chunks = False # Currently not working
token_count_goal = 3000

# for any nested fields move them from the nested structure to the root aka flatten
# Decide what fields you want to keep in the documents
keys_to_keep = { 
    # Root level keys to populate
    "parameters": True,
    "good_responses": True, 
    "bad_responses": False,
    "request_bodies": True, 
    "schemas": True,
    "endpoint_descriptions": True,
    "endpoint_summaries": True, 
    # Keys to exclude
    "enums": True,
    "nested_descriptions": False, 
    "examples": False, 
    "tag_descriptions": False,
    "deprecated": False,
}

methods_to_handle = {"get", "post", "patch", "delete"}

# Saves tokens be abbreviating in a way understood by the LLM
# Must be lowercase
key_abbreviations = {
    "operationid": "opid",
    "parameters": "params",
    "requestbody": "reqBody",
    "properties": "props",
    "schemaname": "schName",
    "description": "desc",
    "summary": "sum",
    "string": "str",
    "number": "num",
    "object": "obj",
    "boolean": "bool",
    "array": "arr",
    "object": "obj"
}

operationID_counter = 0

def load():
        """Load YAML or JSON files."""
        documents = []
        file_extension = None
        for filename in os.listdir(input_filepath):
            if file_extension is None:
                if filename.endswith('.yaml'):
                    file_extension = '.yaml'
                elif filename.endswith('.json'):
                    file_extension = '.json'
                else:
                    raise ValueError(f"Unsupported file format: {filename}")
            elif not filename.endswith(file_extension):
                raise ValueError(f"Inconsistent file formats in directory: {filename}")

            file_path = os.path.join(input_filepath, filename)
            with open(file_path, 'r') as file:
                if file_extension == '.yaml':
                    documents.append(yaml.safe_load(file))
                elif file_extension == '.json':
                    documents.append(json.load(file))
        return documents

def main():
    
    # # Load JSON file into a Python dictionary
    # with open(input_filepath) as f:
    #     openapi_spec = json.load(f)

    openapi_specs = load()
    
    endpoints_by_tag_metadata_dict = defaultdict(list)
    tag_summary_dict = defaultdict(list)
    
    for openapi_spec in openapi_specs:
        # Create list of processed and parsed individual endpoints
        endpoints_by_tag_metadata, tag_summary_dict_output = minify(openapi_spec)
        
        # Append the outputs to the lists
        for key, val in endpoints_by_tag_metadata.items():
            endpoints_by_tag_metadata_dict[key].extend(val)    
        for key, val in tag_summary_dict_output.items():
            tag_summary_dict[key].extend(val)    

    # Sort the data
    sorted_items = sorted(endpoints_by_tag_metadata_dict.items())  
    sorted_endpoints_by_tag_metadata_dict = defaultdict(list, sorted_items)
    sorted_items = sorted(tag_summary_dict.items())  
    sorted_tag_summary_dict = defaultdict(list, sorted_items)
      
    sorted_endpoints_by_tag_metadata_dict, root_output_directory = create_endpoint_files(sorted_endpoints_by_tag_metadata_dict, openapi_spec)
    create_key_point_guide(sorted_endpoints_by_tag_metadata_dict, sorted_tag_summary_dict, root_output_directory)
    count_tokens_in_directory(f'{output_directory}')
    
def minify(openapi_spec):
    
    server_url = openapi_spec['servers'][0]['url']  # Fetch the server URL from the openapi_spec specification
    
    # If the tags key + description doesn't exist at the root of the spec, tags will be added from the endpoints
    tag_summary_dict = {}
    tags = openapi_spec.get('tags')
    if tags:
        # Iterate through the list of tags
        for tag in tags:
            # Extract name and description
            name = tag.get("name")
            description = tag.get("description")
            # Add to the dictionary
            if name and description:
                tag_summary_dict[name] = description.lower()

    # Dictionary with each unique tag as a key, and the value is a list of finalized endpoints with that tag
    endpoints_by_tag = defaultdict(list)
    endpoints_by_tag_metadata = defaultdict(list)
    endpoint_counter = 0
    for path, methods in openapi_spec['paths'].items():
        for method, endpoint in methods.items():
            if method not in methods_to_handle:
                continue
            if endpoint.get('deprecated', False) and not keys_to_keep["deprecated"]:
                continue
            endpoint_counter += 1
            
            # Adds schema to each endpoint
            if keys_to_keep["schemas"]:
                extracted_endpoint_data = resolve_refs(openapi_spec, endpoint)
            else:
                extracted_endpoint_data = endpoint
            
            # Populate output list with desired keys
            extracted_endpoint_data = populate_keys(extracted_endpoint_data, path)

            # If key == None or key == ''
            extracted_endpoint_data = remove_empty_keys(extracted_endpoint_data)

            # Remove unwanted keys
            extracted_endpoint_data = remove_unnecessary_keys(extracted_endpoint_data)

            # Flattens to remove nested objects where the dict has only one key
            extracted_endpoint_data = flatten_endpoint(extracted_endpoint_data)

            # Replace common keys with abbreviations and sets all text to lower case
            extracted_endpoint_data = abbreviate(extracted_endpoint_data, key_abbreviations)
            
            # Get the tags of the current endpoint
            tags = endpoint.get('tags', [])
            tags = [tag for tag in tags]
            if not tags:
                tag = 'default'
            # For each tag, add the finalized endpoint to the corresponding list in the dictionary
            for tag in tags:
                endpoints_by_tag[tag].append(extracted_endpoint_data)

            operation_id = endpoint.get('operationId', '').lower()

            api_url = api_url_format.format(tag=tag, operationId=operation_id)

            context_string = write_dict_to_text(extracted_endpoint_data)
            metadata = {
                'tag': tag,
                'tag_number': 0,
                'doc_number': 0,
                'operation_id': operation_id,
                'doc_url': api_url,
                'server_url': f'{server_url}{path}'
            }
            endpoint_dict = {
                "metadata": metadata,
                "context": context_string
            }

            endpoints_by_tag_metadata[tag].append(endpoint_dict)

    # Sort alphabetically by tag name
    sorted_items = sorted(endpoints_by_tag.items())
    endpoints_by_tag = defaultdict(list, sorted_items)
    # Sort alphabetically by tag name
    sorted_items = sorted(endpoints_by_tag_metadata.items())
    endpoints_by_tag_metadata = defaultdict(list, sorted_items)
    
    # In the case tag_summary_dict is empty or missing tags this adds them here
    for tag in endpoints_by_tag.keys():
        # If the tag is not already in tag_summary_dict, add it with an empty description
        if tag not in tag_summary_dict:
            tag_summary_dict[tag] = ""

    print(f'{endpoint_counter} endpoints found')
    return endpoints_by_tag_metadata, tag_summary_dict
            
def resolve_refs(openapi_spec, endpoint):
    if isinstance(endpoint, dict):
        new_endpoint = {}
        for key, value in endpoint.items():
            if key == '$ref':
                ref_path = value.split('/')[1:]
                ref_object = openapi_spec
                for p in ref_path:
                    ref_object = ref_object.get(p, {})
                
                # Recursively resolve references inside the ref_object
                ref_object = resolve_refs(openapi_spec, ref_object)

                # Use the last part of the reference path as key
                new_key = ref_path[-1]
                new_endpoint[new_key] = ref_object
            else:
                # Recursively search in nested dictionaries
                new_endpoint[key] = resolve_refs(openapi_spec, value)
        return new_endpoint

    elif isinstance(endpoint, list):
        # Recursively search in lists
        return [resolve_refs(openapi_spec, item) for item in endpoint]

    else:
        # Base case: return the endpoint as is if it's neither a dictionary nor a list
        return endpoint

def populate_keys(endpoint, path):
    # Gets the main keys from the specs
    extracted_endpoint_data = {}
    extracted_endpoint_data['path'] = path
    extracted_endpoint_data['operationId'] = endpoint.get('operationId')

    if keys_to_keep["parameters"]:
            extracted_endpoint_data['parameters'] = endpoint.get('parameters')

    if keys_to_keep["endpoint_summaries"]:
            extracted_endpoint_data['summary'] = endpoint.get('summary')

    if keys_to_keep["endpoint_descriptions"]:
            extracted_endpoint_data['description'] = endpoint.get('description')

    if keys_to_keep["request_bodies"]:
            extracted_endpoint_data['requestBody'] = endpoint.get('requestBody')

    if keys_to_keep["good_responses"] or keys_to_keep["bad_responses"]:
        extracted_endpoint_data['responses'] = {}

    if keys_to_keep["good_responses"]:
        if 'responses' in endpoint and '200' in endpoint['responses']:
            extracted_endpoint_data['responses']['200'] = endpoint['responses'].get('200')

    if keys_to_keep["bad_responses"]:
        if 'responses' in endpoint:
            # Loop through all the responses
            for status_code, response in endpoint['responses'].items():
                # Check if status_code starts with '4' or '5' (4xx or 5xx)
                if status_code.startswith('4') or status_code.startswith('5') or 'default' in status_code:
                    # Extract the schema or other relevant information from the response
                    bad_response_content = response
                    if bad_response_content is not None:
                        extracted_endpoint_data['responses'][f'{status_code}'] = bad_response_content
    
    return extracted_endpoint_data

def remove_empty_keys(endpoint):
    if isinstance(endpoint, dict):
        # Create a new dictionary without empty keys
        new_endpoint = {}
        for key, value in endpoint.items():
            if value is not None and value != '':
                # Recursively call the function for nested dictionaries
                cleaned_value = remove_empty_keys(value)
                new_endpoint[key] = cleaned_value
        return new_endpoint
    elif isinstance(endpoint, list):
        # Recursively call the function for elements in a list
        return [remove_empty_keys(item) for item in endpoint]
    else:
        # Return the endpoint if it's not a dictionary or a list
        return endpoint

def remove_unnecessary_keys(endpoint):

    # Stack for storing references to nested dictionaries/lists and their parent keys
    stack = [(endpoint, [])]

    # Continue until there is no more data to process
    while stack:
        current_data, parent_keys = stack.pop()

        # If current_data is a dictionary
        if isinstance(current_data, dict):
            # Iterate over a copy of the keys, as we may modify the dictionary during iteration
            for k in list(current_data.keys()):
                # Check if this key should be removed based on settings and context
                if k == 'example' and not keys_to_keep["examples"]:
                    del current_data[k]
                if k == 'enum' and not keys_to_keep["enums"]:
                    del current_data[k]
                elif k == 'description' and len(parent_keys) > 0 and not keys_to_keep["nested_descriptions"]:
                    del current_data[k]
                # Otherwise, if the value is a dictionary or a list, add it to the stack for further processing
                # Check if the key still exists before accessing it
                if k in current_data and isinstance(current_data[k], (dict, list)):
                    stack.append((current_data[k], parent_keys + [k]))

        # If current_data is a list
        elif isinstance(current_data, list):
            # Add each item to the stack for further processing
            for item in current_data:
                if isinstance(item, (dict, list)):
                    stack.append((item, parent_keys + ['list']))
        
    return endpoint

def flatten_endpoint(endpoint):
    if not isinstance(endpoint, dict):
        return endpoint

    flattened_endpoint = {}

    # Define the set of keys to keep without unwrapping
    keep_keys = {"responses", "default", "200"}
    
    for key, value in endpoint.items():
        if isinstance(value, dict):
            # Check if the dictionary has any of the keys that need to be kept
            if key in keep_keys or (isinstance(key, str) and (key.startswith('5') or key.startswith('4'))):
                # Keep the inner dictionaries but under the current key
                flattened_endpoint[key] = flatten_endpoint(value)
            else:
                # Keep unwrapping single-key dictionaries
                while isinstance(value, dict) and len(value) == 1:
                    key, value = next(iter(value.items()))
                # Recursively flatten the resulting value
                flattened_endpoint[key] = flatten_endpoint(value)
        else:
            # If the value is not a dictionary, keep it as is
            flattened_endpoint[key] = value

    return flattened_endpoint

def abbreviate(data, abbreviations):
    if isinstance(data, dict):
        # Lowercase keys, apply abbreviations and recursively process values
        return {
            abbreviations.get(key.lower(), key.lower()): abbreviate(abbreviations.get(str(value).lower(), value), abbreviations)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        # Recursively process list items
        return [abbreviate(item, abbreviations) for item in data]
    elif isinstance(data, str):
        # If the data is a string, convert it to lowercase and replace if abbreviation exists
        return abbreviations.get(data.lower(), data.lower())
    else:
        # Return data unchanged if it's not a dict, list or string
        return data

def create_endpoint_files(endpoints_by_tag_metadata, openapi_spec):
    
    # Creates a directory named after the API url
    server_url = openapi_spec['servers'][0]['url']  
    parsed_url = urlparse(server_url)
    # If output_directory exists, delete it.
    # If output_directory exists, delete it.
    root_output_directory = os.path.join(output_directory, parsed_url.netloc)

    # Initialize tag and operationId counters
    global operationID_counter
    
    # Create a subdirectory for the operationIDs
    operationIDs_directory = os.path.join(root_output_directory, 'operationIDs')
    os.makedirs(operationIDs_directory, exist_ok=True)

    
    # Now, iterate over each unique tag
    for tag, endpoints_with_tag in endpoints_by_tag_metadata.items():


        for endpoint in endpoints_with_tag:
            endpoint['metadata']['doc_number'] = operationID_counter
   
            # Create a file name 
            file_name = f"{tag}-{operationID_counter}.json"
            # Define the file path
            file_path = os.path.join(operationIDs_directory, file_name)

            # Write the data to a JSON file
            with open(file_path, 'w') as file:
                json.dump(endpoint, file)

            operationID_counter += 1

    return endpoints_by_tag_metadata, root_output_directory

def write_dict_to_text(data):
    def remove_html_tags_and_punctuation(input_str):
        # Strip HTML tags
        no_html_str = re.sub('<.*?>', '', input_str)
        # Define the characters that should be considered as punctuation
        modified_punctuation = set(string.punctuation) - {'/', '#'}
        # Remove punctuation characters
        return ''.join(ch for ch in no_html_str if ch not in modified_punctuation).strip()
    
    # List to accumulate the formatted text parts
    formatted_text_parts = []
    
    # Check if data is a dictionary
    if isinstance(data, dict):
        # Iterate over items in the dictionary
        for key, value in data.items():
            # Remove HTML tags and punctuation from key
            key = remove_html_tags_and_punctuation(key)
            
            # Depending on the data type, write the content
            if isinstance(value, (dict, list)):
                # Append the key followed by its sub-elements
                formatted_text_parts.append(key)
                formatted_text_parts.append(write_dict_to_text(value))
            else:
                # Remove HTML tags and punctuation from value
                value = remove_html_tags_and_punctuation(str(value))
                # Append the key-value pair
                formatted_text_parts.append(f"{key} {value}")
    # Check if data is a list
    elif isinstance(data, list):
        # Append each element in the list
        for item in data:
            formatted_text_parts.append(write_dict_to_text(item))
    # If data is a string or other type
    else:
        # Remove HTML tags and punctuation from data
        data = remove_html_tags_and_punctuation(str(data))
        # Append the data directly
        formatted_text_parts.append(data)
    
    # Join the formatted text parts with a single newline character
    # but filter out any empty strings before joining
    return '\n'.join(filter(lambda x: x.strip(), formatted_text_parts))

def create_key_point_guide(endpoints_by_tag_metadata, tag_summary_dict, root_output_directory):
    # Ensure output directory exists
    os.makedirs(root_output_directory, exist_ok=True)
    # Define output file path
    output_file_path = os.path.join(root_output_directory, 'LLM_OAS_keypoint_guide_file.txt')

    output_string = ''

    # Now, iterate over each unique tag
    for tag, endpoints_with_tag in endpoints_by_tag_metadata.items():
        tag_number = endpoints_with_tag[0].get('metadata', {}).get('tag_number', '')

        # If we're adding tag descriptions and they exist they're added here.
        tag_description = tag_summary_dict.get(tag)
        if keys_to_keep["tag_descriptions"] and tag_description is not None and tag_description != '':
            tag_description = tag_summary_dict.get(tag)
            tag_description = write_dict_to_text(tag_description)
            tag_string = f'{tag}! {tag_description}!!\n'
        else:
            tag_string = f'{tag}!\n'

        for endpoint in endpoints_with_tag:
            # tagtag_number-description\noperation_iddoc_numberoperation_iddoc_number\n
            metadata = endpoint.get('metadata', '')
            doc_number = metadata.get('doc_number', '')
            operation_id = metadata.get('operation_id', '')

            tag_string += f'{operation_id}-{doc_number}!'

        output_string += f'{tag_string}\n'

    print(f'keypoint file token count: {tiktoken_len(output_string)}')
    # Write sorted info_strings to the output file
    with open(output_file_path, 'w') as output_file:
            output_file.write(output_string)

def count_tokens_in_directory(directory):
    token_counts = []
    max_tokens = 0
    max_file = ''
    
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith('.json'):
                filepath = os.path.join(dirpath, filename)
                with open(filepath, 'r') as file:
                    file_content = json.load(file)
                    context_content = file_content.get("context", "")
                    token_count = tiktoken_len(context_content)
                    token_counts.append(token_count)
                    if token_count > max_tokens:
                        max_tokens = token_count
                        max_file = filepath

    print("Total files:", len(token_counts))
    if not token_counts:
        return
    print("Min:", min(token_counts))
    print("Avg:", int(sum(token_counts) / len(token_counts)))
    print("Max:", max_tokens, "File:", max_file)
    print("Total tokens:", int(sum(token_counts)))

    return token_counts

def tiktoken_len(text):
    tokens = tokenizer.encode(
        text,
        disallowed_special=()
    )
    return len(tokens)

main()

    
