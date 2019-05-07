# py-scraper
A python script to scrape Amazon search result and product page

## Requirements
- Python Requests
- Python LXML
- Docker

## Setup Development Environment
Create a virtual environment to isolate the package dependecies locally
```
virtualenv env
source env/bin/activate  # On Windows use `env\Scripts\activate`
```

## Install libraries

```
pip install requests lxml
```

or

```
pip install -r requirements.txt
```

## Run Elasticsearch in docker
```
docker-compose -f "docker-compose.yml" up -d --build
```