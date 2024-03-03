# SpliceAIAPI

API to obtain SpliceAI raw scores.

## Using the image
https://hub.docker.com/r/schnknc/spliceaiapi

```sh
docker pull schnknc/spliceaiapi:main
```


## Environment variables

Note: 
- These environment variables need to be set
- Both the Fasta files are included in the base image (This does result in a large image)

```
GRCH37_FASTA=hg_ref/Homo_sapiens_assembly19.fasta.gz
GRCH38_FASTA=hg_ref/Homo_sapiens_assembly38.fasta.gz
ENSEMBL_TIMEOUT=120 # Timeout in seconds for Ensembl REST API services (seconds)
```

## Running

```sh
docker run --rm \
  -e GRCH37_FASTA=hg_ref/Homo_sapiens_assembly19.fasta.gz \
  -e GRCH38_FASTA=hg_ref/Homo_sapiens_assembly38.fasta.gz \
  -e ENSEMBL_TIMEOUT=120 \
  -p 5001:5001 \
  schnknc/spliceaiapi:main
```

API documentation can be viewed via http://127.0.0.1:5001/docs

# Appendix

## Fasta files source
    
| Files to download | Environment variable |
|-------------------|----------------------|
| https://storage.googleapis.com/gcp-public-data--broad-references/hg19/v0/Homo_sapiens_assembly19.fasta<br>https://storage.googleapis.com/gcp-public-data--broad-references/hg19/v0/Homo_sapiens_assembly19.fasta.fai | `GRCH37_FASTA=/hg_ref/Homo_sapiens_assembly19.fasta` |
| https://storage.googleapis.com/gcp-public-data--broad-references/hg38/v0/Homo_sapiens_assembly38.fasta<br>https://storage.googleapis.com/gcp-public-data--broad-references/hg38/v0/Homo_sapiens_assembly38.fasta.fai | `GRCH38_FASTA=/hg_ref/Homo_sapiens_assembly38.fasta` |
