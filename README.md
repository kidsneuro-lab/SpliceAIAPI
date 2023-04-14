# SpliceAILookup

API to obtain SpliceAI raw scores.

## Set up
* Clone the repository
* Modify .env file to indicate where the hg19 and hg38 fasta files are stored

### Accessing frontend

Note: Frontend can only be accessed when running within VSCode

## Installing virtualenvironment for development
Requirements
* Python 3.9

```shell
python -m virtualenv .venv_spliceaiapi
. .venv_spliceaiapi/bin/activate
pip3 install -U wheel setuptools pip
pip3 install -r requirements_dev.txt
```

## Running tests

```shell
cd SpliceAIAPI
pytest
```

## Building

### Optionally embedding resources
The application requires `hg_ref` resources files. Embedding these at build time will produce a very large image and take significant time to build, but will be fully self-contained and suitable for production. This step may be skipped in favour of supplying these resources at runtime via a host volume
- The files required are
    ```sh
    hg_ref/b37/human_g1k_v37.fasta
    hg_ref/hg38_ref/Homo_sapiens_assembly38.fasta
    ```

### Building the image
```sh
docker build -t splice_ai_api:latest .
```

## Running
The container can be run in two different ways depending on whether the resources files were embedded
- Running using resources that are embedded
    ```sh
    docker run -p 5001:5001 --env-file .env --rm spliceai_api:latest
    ```
- Running using resources on the host (Mac)
    ```sh
    docker run -p 5001:5001 -v ~/Projects/hg_ref:/hg_ref --env-file .env --rm spliceai_api:latest
    ```
- Running using resources on the host (Windows)
    ```sh
    docker run -p 5001:5001 -v //c/hg_ref:/hg_ref --env-file .env --rm spliceai_api:latest    
    ```

## Testing
The endpoints can be tested locally using curl

- get_genomic_coord
    ```sh
    $ curl 'http://localhost:5001/get_genomic_coord/grch38/NM_004006.2:c.4375C%3ET'
    {"chr":"X","pos":"32389644","ref":"G","alt":"A"}
    ```

- get_delta_scores
    ```sh
    curl 'http://localhost:5001/get_delta_scores/' \
    -H 'Content-Type: application/json' \
    --data-raw '{"chrom":"X","pos":"32389644","ref":"G","alt":"A","annotation":"grch38","distance":50,"mask":0}'
    ```
## Publishing the image

- Setup the necessary credentials
    ```sh
    export DOCKERHUB_USERNAME=xxxxxxxxxxxxxxx
    export DOCKERHUB_TOKEN=xxxxxxxxxxxxxxx
    ```

- Login to dockerhub
    ```sh
    echo "$DOCKERHUB_TOKEN" | docker login --username $DOCKERHUB_USERNAME --password-stdin
    ````

- Tag the local image
    ```
    docker image tag myimage registry-host:5000/myname/myimage:latest
    ```

- Push the image to dockerhub
    ```sh
    docker push peterknealecmri/spliceai_api:latest
    ```

    