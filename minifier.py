import json
import os
import tiktoken
from collections import defaultdict
import string
import re
import shutil

tokenizer = tiktoken.encoding_for_model("text-embedding-ada-002")

# input_filepath = 'tatum_swagger.json'
input_filepath = 'stackpath_edge_compute_swagger.json'
output_directory = 'prepared_OAS_docs'
# Generates path to API docs URL for appending to metadata
# api_docs_base_url = "https://apidoc.tatum.io/tag/"
api_docs_base_url = "https://stackpath.dev/reference/"
# Token counts for combined doc
token_count_max = 4500
token_count_goal = 3000


# Handle document number and search/find automation if tags don't exist

# Decide what fields you want to keep in the documents
keys_to_keep = { 
    # Root level keys
    "endpoint_descriptions": True,
    "bad_responses": True, 
    "good_responses": True, 
    "endpoint_summaries": True, 
    "enums": True,
    "parameter_descriptions": True, 
    "examples": True, 
    "tag_descriptions": True,
    "schemas": True,
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
    "array": "arr"
}

def main():
    
    # Load JSON file into a Python dictionary
    with open(input_filepath) as f:
        openapi_spec = json.load(f)

    # Create list of processed and parsed individual endpoints
    endpoints_by_tag, server_url, tag_summary_dict = write_endpoints(openapi_spec)

    # Combine endpoints in groups of tags of relatively the same size token count
    docs = create_balanced_chunks(endpoints_by_tag, server_url)

    # Create LLM OAS keypoint generator guide file 
    # Need to add summaries 
    create_key_point_guide(docs, tag_summary_dict)

    count_tokens_in_directory(f'{output_directory}/endpoints')

def write_endpoints(openapi_spec):
    
    server_url = openapi_spec['servers'][0]['url']  # Fetch the server URL from the openapi_spec specification
    
    # If the tags key doesn't exist at the root of the spec, tags will be added from the endpoints
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
                tag_summary_dict[name] = description

    # Dictionary with each unique tag as a key, and the value is a list of finalized endpoints with that tag
    endpoints_by_tag = defaultdict(list)
    endpoint_counter = 0
    for path, methods in openapi_spec['paths'].items():
        for method, endpoint in methods.items():
            if method not in methods_to_handle:
                continue
            if endpoint.get('deprecated', False) and not keys_to_keep["deprecated"]:
                continue
            endpoint_counter += 1
            
            # Adds schema to each endpoint
            endpoint = resolve_refs(openapi_spec, endpoint)
            
            # Populate output list with desired keys
            extracted_endpoint_data = populate_keys(endpoint, path)
        
            # Remove unnecessary keys
            extracted_endpoint_data = remove_unnecessary_keys(extracted_endpoint_data)

            # Replace common keys with abbreviations and sets all text to lower case
            extracted_endpoint_data = minify(extracted_endpoint_data, key_abbreviations)
            
            # Get the tags of the current endpoint
            tags = endpoint.get('tags', [None])
            
            # For each tag, add the finalized endpoint to the corresponding list in the dictionary
            for tag in tags:
                endpoints_by_tag[tag].append(extracted_endpoint_data)

    # In the case tag_summary_dict is empty or missing tags this adds them here
    for tag in endpoints_by_tag.keys():
        # If the tag is not already in tag_summary_dict, add it with an empty description
        if tag not in tag_summary_dict:
            tag_summary_dict[tag] = ""

    print(f'{endpoint_counter} endpoints found')
    return endpoints_by_tag, server_url, tag_summary_dict
            
def resolve_refs(openapi_spec, endpoint):
    if isinstance(endpoint, dict):
        if '$ref' in endpoint:
            ref_path = endpoint['$ref'].split('/')[1:]
            ref_data = openapi_spec
            for p in ref_path:
                ref_data = ref_data[p]
            ref_data['schemaName'] = ref_path[-1]
            return resolve_refs(openapi_spec, ref_data)
        else:
            return {k: resolve_refs(openapi_spec, v) for k, v in endpoint.items()}
    elif isinstance(endpoint, list):
        return [resolve_refs(openapi_spec, i) for i in endpoint]
    else:
        return endpoint

def populate_keys(endpoint, path):
    # Gets the main keys from the specs
    extracted_endpoint_data = {}
    extracted_endpoint_data['path'] = path
    extracted_endpoint_data['operationId'] = endpoint.get('operationId')
    extracted_endpoint_data['parameters'] = endpoint.get('parameters')
    extracted_endpoint_data['summary'] = endpoint.get('summary')
    
    if 'requestBody' in endpoint:
        requestBody = endpoint['requestBody'].get('content', {}).get('application/json', {}).get('schema')
        if requestBody is not None and 'schemaName' in requestBody:
            requestBody = {'schema': requestBody.pop('schemaName'), **requestBody}  
        extracted_endpoint_data['requestBody'] = requestBody
    
    if keys_to_keep["endpoint_descriptions"]:
        extracted_endpoint_data['description'] = endpoint.get('description')

    if keys_to_keep["good_responses"]:
                if 'responses' in endpoint and '200' in endpoint['responses']:
                    response200 = endpoint['responses']['200'].get('content', {}).get('application/json', {}).get('schema')
                    if response200 is not None and 'schemaName' in response200:
                        response200 = {'schema': response200.pop('schemaName'), **response200}
                    extracted_endpoint_data['200_response'] = response200
            
    if keys_to_keep["bad_responses"]:
        if 'responses' in endpoint:
            # Loop through all the responses
            for status_code, response in endpoint['responses'].items():
                # Check if status_code starts with '4' or '5' (4xx or 5xx)
                if status_code.startswith('4') or status_code.startswith('5'):
                    # Extract the schema or other relevant information from the response
                    bad_response_content = response.get('content', {}).get('application/json', {}).get('schema')
                    if bad_response_content is not None:
                        extracted_endpoint_data[f'{status_code}_response'] = bad_response_content
    
    # You can add similar blocks for other keys
    
    return extracted_endpoint_data

def remove_unnecessary_keys(extracted_endpoint_data):

    # Stack for storing references to nested dictionaries/lists and their parent keys
    stack = [(extracted_endpoint_data, [])]

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
                if k == 'schema' or 'schemaName' and not keys_to_keep["schemas"]:
                    del current_data[k]
                if k == 'enum' and not keys_to_keep["enums"]:
                    del current_data[k]
                elif k == 'description' and 'parameters' in parent_keys and not keys_to_keep["parameter_descriptions"]:
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
        
    return extracted_endpoint_data

def minify(data, abbreviations):
    if isinstance(data, dict):
        # Lowercase keys, apply abbreviations and recursively process values
        return {abbreviations.get(key.lower(), key.lower()): minify(value, abbreviations) for key, value in data.items()}
    elif isinstance(data, list):
        # Recursively process list items
        return [minify(item, abbreviations) for item in data]
    elif isinstance(data, str):
        # If the data is a string, convert it to lowercase
        return data.lower()
    else:
        # Return data unchanged if it's not a dict, list or string
        return data

def create_balanced_chunks(endpoints_by_tag, server_url):
    # If output_directory exists, delete it.
    root_output_directory = os.path.join(output_directory)
    
    # If the directory exists, delete it
    if os.path.exists(root_output_directory):
        shutil.rmtree(root_output_directory)

    # Create a subdirectory called 'endpoints' within the output directory
    endpoints_directory = os.path.join(output_directory, 'endpoints')
    os.makedirs(endpoints_directory, exist_ok=True)

    # Initialize tag and operationId counters
    tag_counter = 0
    docid_counter = 0

    docs = []

    endpoint_counter = 0
    # Now, iterate over each unique tag
    for tag, endpoints_with_tag in endpoints_by_tag.items():

        endpoint_combos = distribute_endpoints(endpoints=endpoints_with_tag, tag=tag, goal_length=token_count_goal)
        for combo in endpoint_combos:
            # Creating a dictionary to hold the information of the combo.
            doc = {"endpoints": []}
            doc_context_string = ''
            for endpoint in combo:
                endpoint_counter += 1
                # Adding each endpoint to the doc
                doc["endpoints"].append(endpoint)
            
                formatted_text = write_dict_to_text(endpoint)
                doc_context_string += f'{formatted_text}\n'

            doc_context_token_count = tiktoken_len(doc_context_string)

            metadata = {
                'tag': tag,
                'tag_number': tag_counter,
                'doc_number': docid_counter,
                'doc_url': f"{api_docs_base_url}{tag}",
                'server_url': server_url,
                'token_count': doc_context_token_count
            }
            doc['metadata'] = metadata

            json_output = {
                "metadata": metadata,
                "doc_context": doc_context_string
            }

            # Create a file name 
            file_name = f"{tag_counter}-{tag}-{docid_counter}-{doc_context_token_count}.json"
            # Define the file path
            file_path = os.path.join(endpoints_directory, file_name)

            # Write the data to a JSON file
            with open(file_path, 'w') as file:
                json.dump(json_output, file)

            docs.append(doc)
            docid_counter += 1
        tag_counter += 1
    print(f'{endpoint_counter} endpoints added to docs')
    return docs

def distribute_endpoints(endpoints, tag, goal_length, depth=0):
    # Build initial combos
    combos = []
    current_combo = []
    combo_token_count = 0
    for index, endpoint in enumerate(endpoints):
        endpoint_token_count= tiktoken_len(write_dict_to_text(endpoint))
        # If too big, truncate operationid
        if endpoint_token_count > token_count_max:
            print(f'truncating: {endpoint["opid"]}\n token count: {endpoint_token_count}')
            operation_id_url = f'endpoint spec too long. see {api_docs_base_url}{tag}/#operation/{endpoint["opid"]} for more info.'
            truncated_endpoint = {
                'path': endpoint['path'],
                'opid': endpoint['opid'],
                'sum': endpoint.get('sum', ''),
                'message': operation_id_url
            }
            endpoints[index] = truncated_endpoint
            endpoint = truncated_endpoint
            endpoint_token_count = tiktoken_len(write_dict_to_text(endpoint))
        if goal_length > (combo_token_count + endpoint_token_count):
            current_combo.append(endpoint)
            combo_token_count += endpoint_token_count
            continue
        # Past here we're creating new combo
        if not current_combo:
            # If current empty add endpoint to current, current to combos, and empty current
            current_combo.append(endpoint)
            combos.append(current_combo)
            current_combo = []
            combo_token_count = 0
        else:
            # If current combo exists append current combo to combos, clear current, and append endpoint to current
            combos.append(current_combo)
            current_combo = []
            current_combo.append(endpoint)
            combo_token_count = endpoint_token_count
 
    # Catch last combo
    if current_combo:
        combos.append(current_combo)
    
    if depth >= 4:
        # Return the combos as is, if maximum recursion depth is reached
        return combos
    
    if len(combos) < 2:
        return combos
    
    # Check if any individual combo's token count is below 65% of the goal_length
    for combo in combos:
        combo_token_counts = [tiktoken_len(write_dict_to_text(endpoint)) for endpoint in combo]
        combo_token_count = sum(combo_token_counts)
        if combo_token_count < goal_length * 0.75:
            if goal_length > token_count_max:
                return combos
            # Increase the goal length by distributing the token count of the first undersized combo
            new_goal_length = goal_length + (combo_token_count / (len(combos) - 1))
            return distribute_endpoints(endpoints=endpoints, tag=tag, goal_length=new_goal_length, depth=depth + 1)

    return combos

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

def create_key_point_guide(docs, tag_summary_dict):

    # Ensure output directory exists
    os.makedirs(output_directory, exist_ok=True)
    # Define output file path
    output_file_path = os.path.join(output_directory, 'LLM_OAS_keypoint_guide_file.txt')

    # List to hold the info_strings
    docs_by_tag = {}
    for doc in docs:
        tag = doc.get('metadata').get('tag')
        if tag:
            if tag not in docs_by_tag:
                docs_by_tag[tag] = []  # Initialize list for this tag
            docs_by_tag[tag].append(doc)
    
    output_string = ''
    for tag, tag_docs in docs_by_tag.items():
            # If we're adding tag descriptions and they exist they're added here.
            if keys_to_keep["tag_descriptions"]:
                tag_description = tag_summary_dict.get(tag)
                if tag_description is not None:
                    tag_description = write_dict_to_text(tag_description)
                    tag_string = f'{tag}-{tag_description}\n'
                else:
                    tag_string = f'{tag}\n'
            else:
                tag_string = f'{tag}\n'
            for doc in tag_docs:
                # Extract the required information from the YAML file
                metadata = doc.get('metadata', '')
                doc_number = metadata.get('doc_number', '')
                endpoints = doc.get('endpoints', [])
                doc_string = f'{doc_number}'
                operation_id_counter = 0
                for endpoint in endpoints:
                    op_id = endpoint.get('opid', '')
                    doc_string += f'{op_id}{operation_id_counter}'
                    operation_id_counter += 1
                tag_string += f'{doc_string}\n'
            output_string += f'{tag_string}'

    print(f'keypoint file token count: {tiktoken_len(output_string)}')
    # Write sorted info_strings to the output file
    with open(output_file_path, 'w') as output_file:
            output_file.write(output_string)

def count_tokens_in_directory(directory):
    token_counts = []
    max_tokens = 0
    max_file = ''
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            with open(os.path.join(directory, filename), 'r') as file:
                file_content = file.read()
                token_count = tiktoken_len(file_content)
                token_counts.append(token_count)
                if token_count > max_tokens:
                    max_tokens = token_count
                    max_file = filename

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

    
