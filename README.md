OpenAPI spec documents are difficult for LLMs to parse, but crucial for interacting with APIs.

The goal of this project is to create usable context for LLMs to either:
* Perform context enriched questions and answering
* Generatively create api calls through agent like behavior

This is required for two reasons:
* Tokens cost money, so reducing token count saves money (while also speeding up response times)
* LLMs have a limited context window; they can only work with so many tokens at a time.
  
An LLM_OAS_keypoint_guide minifies an openapi spec as much as possibly, reducing token count and unlocking compatibility between LLMs and APIs.

**Broad Workflow:**

Query + LLM_OAS_keypoint_guide_file.txt -> LLM -> document number -> openapi spec endpoint description -> LLM -> formatted curl -> API request

```
Prompt:

Dear LLM, we are looking for an endpoint used to resolve the query. The endpoint is described in openapi spec document. The index of the openapi spec is attached. Please locate the proper operationId and document number to resolve the query. The index can be referenced with the following variables: tag, [document number], operationid, [operationid number]. 

Example:

tag
[document number]operationid[operationid number]operationid[operationid number]operationid[operationid number]
[document number]operationid[operationid number]
tag
[document number]operationid[operationid number]...

Query: 

How can I get the details of a stackpath compute instance? Can you create a curl call for me?

keypoint_guide_file:

Infrastructure
0getlocations0
Virtual Machine Images
1getimages0getimagesforfamily1deleteimagesforfamily2createimage3updateimage4getimage5deleteimage6
Metrics
2getmetrics0
Workloads
3getworkloads0
4createworkload0
5getworkload0deleteworkload1
6updateworkload0
Instances
7getworkloadinstances0getworkloadinstance1restartinstance2
Instance Logs
8getlogs0
```
```
Response:

To get the details of a StackPath compute instance, you should use the endpoint that is described under the "Instances" tag in the openapi spec document.

Based on the index provided:

Tag: Instances
Document Number: 7
operationId: getworkloadinstance
operationId Number: 1

This means you need to reference document number 7 and look for the operationId "getworkloadinstance" with the operationId number 1 in the OpenAPI spec document to resolve the query and get the details of a StackPath compute instance.
```
```
Prompt:

Please use the following minified openapi spec document to answer the users query.

Query: 

How can I get the details of a stackpath compute instance? Can you create a curl call for me?

Document:

"path /workload/v1/stacks/stackid/workloads/workloadid/instances\nopid getworkloadinstances\nparams\nname stackid\ndesc a stack id or slug\nin path\nrequired True\nname workloadid\ndesc an edgecompute workload id\nin path\nrequired True\nname pagerequestfirst\ndesc the number of items desired\nin query\nrequired False\nname pagerequestafter\ndesc the cursor value after which data will be returned\nin query\nrequired False\nname pagerequestfilter\ndesc sqlstyle constraint filters\nin query\nrequired False\nname pagerequestsortby\ndesc sort the response by the given field\nin query\nrequired False\nsum get all workload instances\ndesc None\npath /workload/v1/stacks/stackid/workloads/workloadid/instances/instancename\nopid getworkloadinstance\nparams\nname stackid\ndesc a stack id or slug\nin path\nrequired True\nname workloadid\ndesc an edgecompute workload id\nin path\nrequired True\nname instancename\ndesc an edgecompute workload instance name\nin path\nrequired True\nsum get a workload instance\ndesc None\npath /workload/v1/stacks/stackid/workloads/workloadid/instances/instancename/power/restart\nopid restartinstance\nparams\nname stackid\nin path\nrequired True\ndesc a stack id or slug\nname workloadid\nin path\nrequired True\ndesc an edgecompute workload id\nname instancename\nin path\nrequired True\ndesc an edgecompute workload instance name\nsum restart a workload instance\ndesc the action is performed asynchronously and a successful response does not mean the instance has restarted yet\n"
```
```
Response:

To get the details of a StackPath compute instance, you should use the following endpoint:

`GET /workload/v1/stacks/{stackid}/workloads/{workloadid}/instances/{instancename}`

With the operationId `getworkloadinstance`.

Parameters:
- `stackid` (path parameter, required): The ID or slug of the stack.
- `workloadid` (path parameter, required): The ID of the edge compute workload.
- `instancename` (path parameter, required): The name of the edge compute workload instance.

Here's a sample `curl` command to make this API call. Please replace `{stackid}`, `{workloadid}`, `{instancename}`, and `{YOUR_ACCESS_TOKEN}` with the appropriate values:

curl -X GET "https://api.stackpath.com/workload/v1/stacks/{stackid}/workloads/{workloadid}/instances/{instancename}" \
     -H "Authorization: Bearer {YOUR_ACCESS_TOKEN}"


This `curl` command uses the GET method to retrieve the details of the specific StackPath compute instance. You'll need to use an access token for authorization.
```

The above was my first test on StackPath's documentation.

I designed this for the massive Tatum API. I missed some universality and so something are still broken for the StackPath docs. Work in progress.