# Game Scanner

A way to scan the barcode of a boardgame and obtain the bgg id from it.

## How?
Install the requirements and run `main.py`.

## Where?
It's currently deployed somewhere on gcp.
Deploy with `make deploy`.
The data is being saved on Firestore. This is done so that when the barcode leads nowhere or to the wrong game it can be edited.

## What creds
Requires the following credentials in an .env yaml file:
```
GOOGLE_KEY
GOOGLE_CX
BGG_USERNAME
BGG_PASS
```
Google stuff is obtained from [the Programmable Search Engine page](https://programmablesearchengine.google.com/controlpanel/all).

Additionally, a connector to the DB is required. This is obtained by the command
```
gcloud iam service-accounts keys create nraw-key.json \
    --iam-account=<account>@appspot.gserviceaccount.com
```
