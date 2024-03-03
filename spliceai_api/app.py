import traceback
import os
import re
from importlib.resources import files
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from requests import HTTPError
from pydantic import BaseModel, Field

from spliceai.utils import Annotator
from spliceai_api.utils import score_custom_sequence, ensembl_get_genomic_coord, get_delta_scores, Record, validate_fasta, load_annotations

# Determine the logging level based on an environment variable
logging_level = logging.DEBUG if os.getenv("DEBUG") == "true" else logging.INFO

# Configure logging
logging.basicConfig(level=logging_level, format="%(asctime)s %(name)-12s %(funcName)-12s %(levelname)-8s %(message)s")

app = FastAPI(title="SpliceAI API",
              version="SPLICEAI_API_VERSION")

if os.getenv("ALLOW_ALL_ORIGIN"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
else:
    app.add_middleware(
        CORSMiddleware
    )

annotations = load_annotations()
validate_fasta(assemblies=set([annotations[annotation]['fasta'] for annotation in annotations.keys()]))

dna_pattern = re.compile("^[ATCG]+$")

class DefaultException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


@app.exception_handler(DefaultException)
async def unicorn_exception_handler(request: Request, exc: DefaultException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

class Variant(BaseModel):
    chrom: str
    pos: int
    ref: str
    alt: str
    annotation: str
    distance: int = Field(description="Maximum distance between the variant and gained/lost splice site (default: 50).", default=50, gt=49, lt=10001)
    mask: int = Field(description="Mask scores representing annotated acceptor/donor gain and unannotated acceptor/donor loss (default: 0).", default=0)

@app.get("/health/alive")
def get_alive():
    return {"status": "alive"}


@app.get("/health/ready")
def get_ready():
    return {"status": "ready"}

@app.get("/get_annotations")
async def api_get_annotations():
    return annotations

@app.get("/score_custom_seq/{sequence}")
async def api_score_custom_seq(sequence: str):
    if not dna_pattern.match(sequence):
        raise DefaultException(status_code=400, detail=jsonable_encoder(
            {'summary':'DNA string must contain ATCG',
             'details':f"Entered sequence must contain ATCG and not be blank"}))
    return score_custom_sequence(sequence=sequence)


@app.get("/get_genomic_coord/{assembly}/{variant}")
async def api_get_genomic_coord(variant: str, assembly: str = 'grch38') -> dict:
    """Obtain genomic coordinates for a given variant

    Args:
        variant (str): Variant. This can be HGVSc, HGVSg
        assembly (str): 'grch38' or 'grch37'

    Returns:
        dict: Genomic coordinates consisting of 'chr', 'pos', 'ref' and 'alt'
    """
    if assembly not in annotations.keys():
        raise DefaultException(status_code=400, detail=jsonable_encoder(
            {'summary':'Invalid assembly',
             'details':f"{assembly} is not a valid assembly"}))

    try:
        gcoord = ensembl_get_genomic_coord(variant=variant, assembly=annotations[assembly]['assembly'])
        return(gcoord)
    except HTTPError as e:
        raise HTTPException(status_code=e.response.status_code, detail=jsonable_encoder(
            {'summary':'Encountered error while translating variant',
             'details': e.response.json()['error']}))
    except Exception as e:
        raise DefaultException(status_code=500, detail=jsonable_encoder(
            {'summary':'Encountered error while translating variant',
             'details':e.__doc__}))
        

@app.post("/get_delta_scores/")
async def api_get_delta_scores(variant: Variant):
    record = Record(chrom=variant.chrom, pos=variant.pos, ref=variant.ref, alts=[variant.alt])

    annotation_file = None

    if variant.annotation in ['grch37','grch38']:
        annotation_file = variant.annotation
    else:
        annotation_file = files("spliceai_api.annotations").joinpath(f"{variant.annotation}.txt")

    try:
        ann = Annotator(os.getenv(annotations[variant.annotation]['fasta']), annotation_file)
        return get_delta_scores(record, ann, variant.distance, variant.mask)
    except Exception as e:
        traceback.print_exc()
        raise DefaultException(status_code=500, detail=jsonable_encoder(
            {'summary':'Encountered error while calculating SpliceAI scores',
             'details':e.__doc__}))