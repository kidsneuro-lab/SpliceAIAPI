# SpliceAIAPI

API to obtain SpliceAI scores for a genetic variant or assess scores for a raw sequence.

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
GRCH37_FASTA=/hg_ref/Homo_sapiens_assembly19.fasta.gz
GRCH38_FASTA=/hg_ref/Homo_sapiens_assembly38.fasta.gz
```

## Running

**IMPORTANT:** Packing the fasta files within the docker image was attempted. Storing them in an uncompressed state
occupies a lot of space. However after compressing them (using `bgzip` and indexing using `pyfaidx`'s `faidx` command), CPU utilisation when retrieving the sequence was unusually high. Feel to submit a PR if you figure out a way to build a fully contained image.

1. Download Human genome reference files.

```sh
wget -qc https://github.com/broadinstitute/gatk/raw/master/src/test/resources/large/Homo_sapiens_assembly19.fasta.gz
wget -qc https://github.com/broadinstitute/gatk/raw/master/src/test/resources/large/Homo_sapiens_assembly19.fasta.gz.fai
wget -qc https://github.com/broadinstitute/gatk/raw/master/src/test/resources/large/Homo_sapiens_assembly19.fasta.gz.gzi

wget -qc https://github.com/broadinstitute/gatk/raw/master/src/test/resources/large/Homo_sapiens_assembly38.fasta.gz
wget -qc https://github.com/broadinstitute/gatk/raw/master/src/test/resources/large/Homo_sapiens_assembly38.fasta.gz.fai
wget -qc https://github.com/broadinstitute/gatk/raw/master/src/test/resources/large/Homo_sapiens_assembly38.fasta.gz.gzi
```

2. Move these files to `hg_ref` folder.

3. Download `docker-compose-nginx.yml` to the folder where you want to start running this service.

3. Download `nginx` folder. This contains a bare bones nginx configuration.

4. Launch container. This will start up the container.
```sh
docker compose -f docker-compose-nginx.yml up -d
```

API documentation can be viewed via http://127.0.0.1/spliceai/api/v1/docs

## Examples

### Score custom sequence
```sh
curl "http://127.0.0.1:5001/spliceai/api/v1/score_custom_seq/GATGGGGTCGCGAGGGTGTGGCAGGGG" \
     -H 'Accept: application/json'
```

```json
{
  "acceptor_prob": [
    1.5418306702486007e-06,
    1.9345423424965702e-05,
    3.8379903344321065e-07,
    1.029576878863736e-06,
    ...
    1.4519804381052381e-06,
    3.9281672798097134e-05,
    1.907279170154652e-06,
    2.258779659314314e-06
  ],
  "donor_prob": [
    2.966317538266594e-07,
    1.352084666450537e-07,
    2.6359310822954285e-07,
    7.184016226347012e-08,
    ...
    6.75224782753503e-07,
    9.227094892594323e-07,
    1.6579800785621046e-06,
    4.530704700300703e-07
  ]
}
```

### Single variant
```sh
curl -X "POST" "http://127.0.0.1:5001/spliceai/api/v1/get_delta_scores/" \
     -H 'Content-Type: application/json' \
     -H 'Accept: application/json' \
     -d $'{
  "ref": "C",
  "distance": 500,
  "chrom": "21",
  "alt": "A",
  "mask": 0,
  "annotation": "grch38",
  "pos": 26840275
}'
```

```json
[
  {
    "gene": "ADAMTS1",
    "strand": "-",
    "chr": "21",
    "pos": 26840275,
    "ref": "C",
    "alt": "A",
    "stats": [
      {
        "dist_from_variant": -500,
        "donor_ref": 1.739998367611406e-08,
        "donor_alt": 2.060303039286282e-08,
        "donor": 3.2030467167487586e-09,
        "acceptor_ref": 4.3531332494239905e-07,
        "acceptor_alt": 4.515591172093991e-07,
        "acceptor": 1.624579226700007e-08
      },
      ...
      {
        "dist_from_variant": 500,
        "donor_ref": 3.397376957536835e-08,
        "donor_alt": 2.1447513987027378e-08,
        "donor": -1.2526255588340973e-08,
        "acceptor_ref": 1.1092862628458988e-08,
        "acceptor_alt": 1.0934412486562906e-08,
        "acceptor": -1.5845014189608264e-10
      }
    ]
  }
]
```

### Bulk variants
```sh
curl -X "POST" "http://127.0.0.1:5001/spliceai/api/v1/get_bulk_delta_scores/" \
     -H 'Content-Type: application/json' \
     -H 'Accept: application/json' \
     -d $'{
  "annotation": "grch38",
  "mask": 0,
  "distance": 50,
  "variants": [
    {
      "chrom": "21",
      "pos": 32657714,
      "alt": "G",
      "ref": "A"
    },
    {
      "chrom": "21",
      "pos": 43426016,
      "alt": "T",
      "ref": "C"
    }
  ]
}'
```

```json
[
  {
    "input": "21-32657714-A-G",
    "scores": [
      {
        "gene": "SYNJ1",
        "strand": "-",
        "chr": "21",
        "pos": 32657714,
        "ref": "A",
        "alt": "G",
        "stats": [
          {
            "dist_from_variant": -50,
            "donor_ref": 4.111615794499812e-07,
            "donor_alt": 3.9448965253541246e-05,
            "donor": 3.903780452674255e-05,
            "acceptor_ref": 4.4938190946197665e-09,
            "acceptor_alt": 2.6050091861407054e-08,
            "acceptor": 2.1556273210876498e-08
          },
          ...
          {
            "dist_from_variant": 50,
            "donor_ref": 1.982020165769427e-07,
            "donor_alt": 1.4615977761422982e-06,
            "donor": 1.2633958021979197e-06,
            "acceptor_ref": 5.44833881122031e-07,
            "acceptor_alt": 3.612714749579027e-07,
            "acceptor": -1.8356240616412833e-07
          }
        ]
      }
    ],
    "error": null
  },
  {
    "input": "21-43426016-C-T",
    "scores": [
      {
        "gene": "SIK1",
        "strand": "-",
        "chr": "21",
        "pos": 43426016,
        "ref": "C",
        "alt": "T",
        "stats": [
          {
            "dist_from_variant": -50,
            "donor_ref": 2.058185089026665e-07,
            "donor_alt": 1.1728113946674057e-07,
            "donor": -8.853736943592594e-08,
            "acceptor_ref": 1.476289810398157e-07,
            "acceptor_alt": 1.1874813310441823e-07,
            "acceptor": -2.888084793539747e-08
          },
          ...
          {
            "dist_from_variant": 50,
            "donor_ref": 4.603280103765428e-07,
            "donor_alt": 3.017120207005064e-07,
            "donor": -1.586159896760364e-07,
            "acceptor_ref": 1.9619160411821213e-06,
            "acceptor_alt": 2.258359472762095e-06,
            "acceptor": 2.9644343157997355e-07
          }
        ]
      }
    ],
    "error": null
  }
]
```
