# OpenAPI spec minification for LLM context docs


## Goal: extend the context of LLMs by prompt stuffing with API documentation

### Enabling: 
* Context enriched questions and answering on API documentation
* Natural language interactions with APIs

### What does that mean? 

You can create an app that *only* needs the API documentation to respond to natural language queries like:

`Can you make the hue lights in my office look better for a video call even though it's dark outside?` 

`Has there been any news about today's f1 race?`

`Was there an earthquake in Texas today? My apartment in Dallas was swaying just now.`

`How many open issues are there on my repo right now?`

---
### The Challenge:
* OpenAPI spec documents are not suitable for providing context to LLMs
  * They can be massive; vastly exceeding the token count limits and context windows of LLMs
  * They are not formatted to be human readable or even machine readable
* Even if an OAS could be made to work with an LLM it would still be a bad solution.
  * The majority of an OAS's characters, and therefore tokens, are meaningless to an LLM and therefore wasted.
  * LLM providers charge on a token count basis as it correlates with compute utilization, and so there is a real monetary/energy/carbon cost for burning tokens.
  * Token count correlates with processing time, and so minimizing token count where ever possible reduces response time making for a better user experience.

### A Solution is minification:
* Minification in this context means to reduce the character count, and therefore token count, of a APIs documentation as much as possible. This is straight forward: if a character is not useful, it's removed. This script does things like:
  *  Replacing common words with abbreviations. For example `string` -> `str`
  *  Removing spaces, newlines, and other punctuation.
  *  Removing empty keys or meaningless key value pairs.
* Additionally, this script resolves references, and has some other QoL features like metadata linking to official documentation.

<details>
<summary>Endpoint before minification</summary>

Fully rendered with the `$ref` components this would be much longer.
```
  "paths": {
      "/workload/v1/locations": {
        "get": {
          "summary": "Get compute locations",
          "operationId": "GetLocations",
          "responses": {
            "200": {
              "description": "",
              "content": {
                "application/json": {
                  "schema": {
                    "$ref": "#/components/schemas/v1GetLocationsResponse"
                  }
                }
              }
            },
            "401": {
              "description": "Returned when an unauthorized request is attempted.",
              "content": {
                "application/json": {
                  "schema": {
                    "$ref": "#/components/schemas/stackpathapiStatus"
                  }
                }
              }
            },
            "500": {
              "description": "Internal server error.",
              "content": {
                "application/json": {
                  "schema": {
                    "$ref": "#/components/schemas/stackpathapiStatus"
                  }
                }
              }
            },
            "default": {
              "description": "Default error structure.",
              "content": {
                "application/json": {
                  "schema": {
                    "$ref": "#/components/schemas/stackpathapiStatus"
                  }
                }
              }
            }
          },
          "parameters": [
            {
              "name": "page_request.first",
              "description": "The number of items desired.",
              "in": "query",
              "required": false,
              "schema": {
                "type": "string"
              }
            },
            {
              "name": "page_request.after",
              "description": "The cursor value after which data will be returned.",
              "in": "query",
              "required": false,
              "schema": {
                "type": "string"
              }
            },
            {
              "name": "page_request.filter",
              "description": "SQL-style constraint filters.",
              "in": "query",
              "required": false,
              "schema": {
                "type": "string"
              }
            },
            {
              "name": "page_request.sort_by",
              "description": "Sort the response by the given field.",
              "in": "query",
              "required": false,
              "schema": {
                "type": "string"
              }
            }
          ],
          "tags": [
            "Infrastructure"
          ],
          "description": "Retrieve information about the StackPath edge network that can host a compute workload"
        }
      },
```
</details>

<details>
<summary>Endpoint after minification</summary>

```
"path /workload/v1/locations\nopid getlocations\nparams\nname pagerequestfirst\nin query\nrequired False\nschema\ntype str\nname pagerequestafter\nin query\nrequired False\nschema\ntype str\nname pagerequestfilter\nin query\nrequired False\nschema\ntype str\nname pagerequestsortby\nin query\nrequired False\nschema\ntype str\nsum get compute locations\ndesc retrieve information about the stackpath edge network that can host a compute workload\nresponses\n200\nv1getlocationsresponse\ntype obj\nprops\npaginationpageinfo\ntype obj\nprops\ntype str\nhaspreviouspage\ntype bool\nformat bool\nhasnextpage\ntype bool\nformat bool\nresults\ntype arr\nworkloadv1location\ntype obj\nprops\ntype str\nlatitude\ntype num\nformat double\nlongitude\ntype num\nformat double"}
```
</details>

---

## Why does this work?
* This minified OAS documentation is *much* smaller, yet still provides the information an an LLM needs!.
  * Because LLMs are trained on thousands of other OAS docs it knows what to expect, and can extract the information it needs to conceptualize the document.
  * Much of what was removed is structurally important for programmatic uses of the document like JSON formatting or rendering of human readable documentation. It's useless here.

---

## Perform a manual PoC test:
<details>
<summary>Test Workflow</summary>

### 1. Create your query
* Copy the entire contents of a LLM_OAS_keypoint_guide_file.txt file from one of the example folders.
* Append your query to the top or bottom of the query.
* Paste it into your LLM (GPT 3.5 is fine).
<details>
<summary>Example Query: Can you help me check the latest block number on solana?</summary>

```
Query: Can you help me check the latest block number on solana?

dear agent,
the user has a query that can be answered with an openapi spec document
please use this llm parsable index of openapi spec documentation in the format:
{{tag_number}}{{tag}} {{tag_description}}
{{operationId}}{{doc_number}}{{operationId}}{{doc_number}}...
{{tag_number}}{{tag}}
...

each operationId in has an associated doc_number 
using this index please return the most relevant operationIds
do so STRICTLY by specifying in the following format 
IMPORTANTLY REPLY ONLY with numbers and \n characters:

{{tag_number}}
{{doc_number}}
{{doc_number}}
...
\n
{{tag_number}}
...
thank you agent,
begin

0Account
createaccount0getaccounts1getaccountscount2createaccountbatch3getaccountsbycustomerid4getaccountbyaccountid5getaccountbalance6blockamount7deleteblockamount8getblockamount9getblockamountbyid10deleteallblockamount11
1Algorand
algorandgeneratewallet0algorandgenerateaddress1algorandgetbalance2algorandgetcurrentblock3algorandgetblock4algorandblockchaintransfer5algorandblockchainreceiveasset6algorandgettransaction7algorandbroadcast8
2Auction
generateauction0createauction1bidonauction2settleauction3cancelauction4approvenftauctionspending5getauction6getauctionfee7getauctionfeerecipient8
3BNB Beacon Chain
bnbgeneratewallet0bnbgetcurrentblock1bnbgetblock2bnbgetaccount3bnbgettransaction4bnbgettxbyaccount5bnbblockchaintransfer6bnbbroadcast7
4BNB Smart Chain
bscgeneratewallet0bscgenerateaddress1bscgenerateaddressprivatekey2bscgetcurrentblock3bscgetblock4bscgetbalance5bscgettransaction6bscgettransactioncount7bscblockchaintransfer8bscblockchainsmartcontractinvocation9bscbroadcast10
5Bitcoin
btcgeneratewallet0btcgenerateaddress1btcgenerateaddressprivatekey2btcgetblockchaininfo3btcgetblockhash4btcgetblock5btcgetbalanceofaddress6btcgetbalanceofaddressbatch7btcgettxbyaddress8btctransferblockchain9btcgetrawtransaction10btcgetutxo11btcgetmempool12btcbroadcast13
6Bitcoin Cash
bchgeneratewallet0bchgetblockchaininfo1bchgetblockhash2bchgetblock3bchgetrawtransaction4bchgettxbyaddress5bchgenerateaddress6bchgenerateaddressprivatekey7bchtransferblockchain8bchbroadcast9
7Blockchain addresses
generatedepositaddress0getalldepositaddresses1generatedepositaddressesbatch2addressexists3assignaddress4removeaddress5
8Blockchain fees
getblockchainfee0estimatefeeblockchain1bscestimategas2celoestimategas3egldestimategas4ethestimategas5ethestimategasbatch6oneestimategas7klaytnestimategas8kcsestimategas9polygonestimategas10xdcestimategas11vetestimategas12
9Blockchain operations
btctransfer0bchtransfer1ltctransfer2flowtransfer3dogetransfer4ethtransfer5polygontransfer6kcstransfer7ethtransfererc208ethdeployerc209bscorbeptransfer10bscdeploybep2011klaytransfer12klaydeployerc2013xdctransfer14xdcdeployerc2015onetransfer16onedeployhrm2017registererc20token18storetokenaddress19celoorerc20transfer20celodeployerc20ledger21kcsdeployerc20ledger22soltransfer23xlmtransfer24xlmassetoffchain25xrptransfer26xrpassetoffchain27bnbtransfer28bnbassetoffchain29adatransferoffchain30trontransferoffchain31createtrc32trondeploytrc33egldtransfer34algodeployerc20ledger35algotransfer36
10Blockchain storage
storelog0getlog1
11Blockchain utils
scgetcontractaddress0getauctionestimatedtime1
12Cardano
adagetblockchaininfo0adageneratewallet1adagenerateaddress2adagenerateaddressprivatekey3adagetblock4adagetrawtransaction5adagettxbyaddress6adagetutxobyaddress7adatransferblockchain8adabroadcast9adagetaccount10
13Celo
celogeneratewallet0celogenerateaddress1celogenerateaddressprivatekey2celogetcurrentblock3celogetblock4celogetbalance5celogettransactionbyaddress6celogettransaction7celogettransactioncount8celoblockchaintransfer9celoblockchainsmartcontractinvocation10celobroadcast11
14Custodial managed wallets
custodialcreatewallet0custodialgetwallets1custodialgetwallet2custodialdeletewallet3custodialtransfermanagedaddress4
15Customer
findallcustomers0getcustomerbyexternalorinternalid1
16Data API
getcollections0getmetadata1getbalances2getowners3checkowner4gettransactions5gettransactionsbyhash6getevents7getblocks8getlatestblock9gettokens10getutxosbyaddress11
17Deposit
getdeposits0getdepositscount1
18Dogecoin
dogegeneratewallet0dogegenerateaddress1dogegenerateaddressprivatekey2dogegetblockchaininfo3dogegetblockhash4dogegetblock5dogegetrawtransaction6dogegettxbyaddress7dogegetbalanceofaddress8dogegetbalanceofaddressbatch9dogegetmempool10dogegetutxo11dogetransferblockchain12dogebroadcast13
19Elrond
egldgeneratewallet0egldgenerateaddress1egldgenerateaddressprivatekey2egldgetcurrentblock3egldgetblock4egldgetbalance5egldgettransaction6egldgettransactionaddress7egldgettransactioncount8egldblockchaintransfer9egldbroadcast10
20Ethereum
ethgeneratewallet0ethgenerateaddress1ethgenerateaddressprivatekey2ethgetcurrentblock3ethgetblock4ethgetbalance5ethgettransaction6ethgettransactioncount7ethgettransactionbyaddress8ethblockchaintransfer9ethblockchainsmartcontractinvocation10ethgetinternaltransactionbyaddress11ethbroadcast12
21Exchange rate
getexchangerate0getexchangerates1
22Flow
flowgeneratewallet0flowgenerateaddress1flowgeneratepubkey2flowgeneratepubkeyprivatekey3flowgetblockchaininfo4flowgetblock5flowgetblockevents6flowgetrawtransaction7flowgetaccount8flowtransferblockchain9flowtransfercustomblockchain10flowcreateaddressfrompubkey11
23Fungible Tokens (ERC-20 or compatible)
erc20deploy0erc20mint1erc20burn2erc20approve3erc20transfer4erc20gettransactionbyaddress5erc20getbalance6erc20getbalanceaddress7
24Gas pump
precalculategaspumpaddresses0activategaspumpaddresses1activatednotactivatedgaspumpaddresses2gaspumpaddressesactivatedornot3transfercustodialwallet4transfercustodialwalletbatch5approvetransfercustodialwallet6
25Harmony
onegeneratewallet0onegenerateaddress1oneformataddress2onegenerateaddressprivatekey3onegetcurrentblock4onegetblock5onegetbalance6onegettransaction7onegettransactioncount8oneblockchaintransfer9oneblockchainsmartcontractinvocation10onebroadcast11
26IPFS
getipfsdata0storeipfs1
27Key Management System
getpendingtransactionstosign0receivependingtransactionstosign1getpendingtransactiontosign2deletependingtransactiontosign3
28Klaytn
klaytngeneratewallet0klaytngenerateaddress1klaytngenerateaddressprivatekey2klaytngetcurrentblock3klaytngetblock4klaytngetbalance5klaytngettransaction6klaytngettransactioncount7klaytnblockchaintransfer8klaytnblockchainsmartcontractinvocation9klaytnbroadcast10
29KuCoin
kcsgeneratewallet0kcsgenerateaddress1kcsgenerateaddressprivatekey2kcsgetcurrentblock3kcsgetblock4kcsgetbalance5kcsgettransaction6kcsgettransactioncount7kcsblockchaintransfer8kcsblockchainsmartcontractinvocation9kcsbroadcast10
30Litecoin
ltcgeneratewallet0ltcgetblockchaininfo1ltcgetblockhash2ltcgetblock3ltcgetrawtransaction4ltcgetmempool5ltcgettxbyaddress6ltcgetbalanceofaddress7ltcgetbalanceofaddressbatch8ltcgetutxo9ltcgenerateaddress10ltcgenerateaddressprivatekey11ltctransferblockchain12ltcbroadcast13
31Malicious address
checkmalicousaddress0
32Marketplace
generatemarketplace0sellassetonmarketplace1buyassetonmarketplace2cancelsellmarketplacelisting3getmarketplacelistings4getmarketplacelisting5getmarketplaceinfo6getmarketplacefee7getmarketplacefeerecipient8withdrawfeefrommarketplace9withdrawtreasuryfrommarketplace10
33Multi Tokens (ERC-1155 or compatible)
deploymultitoken0mintmultitoken1mintmultitokenbatch2burnmultitoken3burnmultitokenbatch4transfermultitoken5transfermultitokenbatch6addmultitokenminter7multitokengettransactionbyaddress8multitokengettransaction9multitokengetaddressbalance10multitokengetbalance11multitokengetbalancebatch12multitokengetmetadata13
34NFT (ERC-721 or compatible)
nftdeployerc7210nftaddminter1nftminterc7212nfttransfererc7213nftmintmultipleerc7214nftburnerc7215nftverifyincollection6nftgettransactionbyaddress7nftgettransactionbytoken8nftgettransacterc7219nftgettokensbyaddresserc72110nftgettokensbycollectionerc72111nftgetbalanceerc72112nftgetmetadataerc72113
35Node RPC
nodejsonpostrpcdriver0nodejsonrpcgetdriver1
36Notification subscriptions
createsubscription0getsubscriptions1disablewebhookhmac2getsubscriptionscount3deletesubscription4getsubscriptionreport5getallwebhooks6getallwebhookscount7
37Order Book
storetrade0chartrequest1gethistoricaltradesbody2getbuytradesbody3getselltradesbody4getmatchedtrades5gettradebyid6deletetrade7deleteaccounttrades8
38Polygon
polygongeneratewallet0polygongenerateaddress1polygongenerateaddressprivatekey2polygongetcurrentblock3polygongetblock4polygongetbalance5polygongettransaction6polygongettransactionbyaddress7polygongettransactioncount8polygonblockchaintransfer9polygonblockchainsmartcontractinvocation10polygonbroadcast11
39Service utils
getcredits0getversion1unfreezeapikey2
40Solana
solanageneratewallet0solanagetcurrentblock1solanagetblock2solanagetbalance3solanagettransaction4solanablockchaintransfer5solanabroadcastconfirm6
41Stellar
xlmwallet0xlmgetlastclosedledger1xlmgetledger2xlmgetledgertx3xlmgetfee4xlmgetaccounttx5xlmgettransaction6xlmgetaccountinfo7xlmtransferblockchain8xlmtrustlineblockchain9xlmbroadcast10
42Transaction
sendtransaction0sendtransactionbatch1gettransactionsbyaccountid2gettransactionsbycustomerid3gettransactions4gettransactionsbyreference5
43Tron
generatetronwallet0trongenerateaddress1trongenerateaddressprivatekey2trongetcurrentblock3trongetblock4trongetaccount5tronfreeze6tronunfreeze7tronaccounttx8tronaccounttx209trontransfer10trontransfertrc1011trontransfertrc2012troncreatetrc1013trontrc10detail14troncreatetrc2015trongettransaction16tronbroadcast17
44VeChain
vetgeneratewallet0vetgenerateaddress1vetgenerateaddressprivatekey2vetgetcurrentblock3vetgetblock4vetgetbalance5vetgetenergy6vetgettransaction7vetgettransactionreceipt8vetblockchaintransfer9vetbroadcast10
45Virtual Currency
createcurrency0getcurrency1
46Virtual account blockchain fees
offchainestimatefee0
47Withdrawal
storewithdrawal0getwithdrawals1cancelinprogresswithdrawal2broadcastblockchaintransaction3
48XRP
xrpwallet0xrpgetlastclosedledger1xrpgetfee2xrpgetaccounttx3xrpgetledger4xrpgettransaction5xrpgetaccountinfo6xrpgetaccountbalance7xrptransferblockchain8xrptrustlineblockchain9xrpaccountsettings10xrpbroadcast11
49XinFin
xdcgeneratewallet0xdcgenerateaddress1xdcgenerateaddressprivatekey2xdcgetcurrentblock3xdcgetblock4xdcgetbalance5xdcgettransaction6xdcgettransactioncount7xdcblockchaintransfer8xdcblockchainsmartcontractinvocation9xdcbroadcast10
```
</details>

### 2. LLM responds with... numbers??
```
40
1
```
### 3. Find the file matching those numbers in the example folder 
* The first number is the tag number and the second number is the document number
* In our case tag number 40 represents the `solana` tag, and document number 1 represents the operationId `solanagetcurrentblock`.

### 4. Paste this whole content of the document and the original query into the LLM
```
Query: Can you help me check the latest block number on solana?
{"metadata": {"tag": "Solana", "tag_number": 40, "doc_number": 1, "operation_id": "solanagetcurrentblock", "doc_url": "https://apidoc.tatum.io/tag/Solana#operation/solanagetcurrentblock", "server_url": "https://api.tatum.io/v3/solana/block/current"}, "context": "path /v3/solana/block/current\nopid solanagetcurrentblock\nsum get current block number\ndesc 1 credit per api callget solana current block number this is the number of the latest block in the blockchain\nresponses\n200\ntype num"}
```

### 5. LLM responds
* Note: You may need to refresh the LLM or switch to GPT-4.
* Remember this test is a PoC. In real life you'd have a seperate prompt template for this step.
* With the above pasted into GPT-4 I get:

```
Sure, I can help you with that. Let me fetch the latest block number on Solana for you.

The current block number on Solana can be obtained by making a GET request to the following endpoint:
```
```
bash

GET https://api.tatum.io/v3/solana/block/current
```
```
Please note that you may need to include any required authentication or API keys when making the request.

Once you make the request, you will receive a response with a status code of 200 and the block number will be returned as a number in the response body.

For more details on the API endpoint, you can refer to the documentation at this link.

Let me know if there's anything else I can assist you with!
```
### The point of this PoC isn't that you would do this manually, but you could easily build an agent to programtically do this.

</details>

---

## Programtic workflow for using natural language to interact with an API

### 1. Create initial prompt using LLM_OAS_keypoint_guide and query
* The LLM_OAS_keypoint_guide contains an indexed list of all endpoints available on the API
* The endpoints are indexed via a system of tag numbers and document numbers that correspond to files in the example folders
* The prompt instructs the LLM to ONLY respond with numbers correlating to the relevant documents.
  * This will be further enforced with logit biasing
  * Essentially, with this setting you can force GPT to ONLY respond with numbers
  * https://help.openai.com/en/articles/5247780-using-logit-bias-to-define-token-probability
### 2. Locate file from response and append query + prompt template
* The content from the file specified by the LLM will be used to genarate the API call request
* You will need to specificy here the format of this request with an additional prompt template

### 3. Send a function request to GPT3.4 to create your API request

### 4. With the generated API request your application can now call the API

## Use

* Clone it or download it. 
* Put your OAS json in the folder. Change the settings at the top of the script to point to your file.
* Change the settings to meet your use case. Certain keys can be enabled or disable.
* Feel free to add more abbreviations and create a PR.
* Run it. Use the files to power your langchain or other app.