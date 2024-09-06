import traceback
import os
import re
from importlib.resources import files
import logging
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from requests import HTTPError
from pydantic import BaseModel, Field

from spliceai_api.exceptions import SpliceAIAPIException
from spliceai_api.utils import score_custom_sequence, ensembl_get_genomic_coord, get_delta_scores, Record, validate_fasta, load_annotations, Annotator
from spliceai_api import MODELS

# Determine the logging level based on an environment variable
logging_level = logging.DEBUG if os.getenv("DEBUG") == "true" else logging.INFO

# Configure logging
logging.basicConfig(level=logging_level, format="%(asctime)s %(name)-12s %(funcName)-12s %(levelname)-8s %(message)s")

version = os.getenv("VERSION","UNKNOWN")
app = FastAPI(title="SpliceAI API",version=version)

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

dna_pattern = re.compile("^[ATCGN]+$")

class DefaultException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


@app.exception_handler(DefaultException)
async def unicorn_exception_handler(request: Request, exc: DefaultException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail['summary'],
            "details": exc.detail['details']
        },
    )

class SingleVariant(BaseModel):
    chrom: str
    pos: int
    ref: str
    alt: str
    annotation: Literal["grch38","grch37","grch38_custom","grch37_custom"]
    distance: int = Field(description="Maximum distance between the variant and gained/lost splice site (default: 50).", default=50, gt=49, lt=10001)
    mask: int = Field(description="Mask scores representing annotated acceptor/donor gain and unannotated acceptor/donor loss (default: 0).", default=0)

class BulkVariant(BaseModel):
    chrom: str
    pos: int
    ref: str
    alt: str

class BulkVariantList(BaseModel):
    annotation: Literal["grch38","grch37","grch38_custom","grch37_custom"]
    distance: int = Field(description="Maximum distance between the variant and gained/lost splice site (default: 50).", default=50, gt=49, lt=10001)
    mask: int = Field(description="Mask scores representing annotated acceptor/donor gain and unannotated acceptor/donor loss (default: 0).", default=0)
    variants: list[BulkVariant]

class Stats(BaseModel):
    dist_from_variant: int = Field(description="Offset from variant")
    donor_ref: float = Field(description="Reference probability that this position is a donor")
    donor_alt: float = Field(description="Altered probability that this position is a donor")
    donor: float = Field(description="Difference between Altered and Reference")
    acceptor_ref: float = Field(description="Reference probability that this position is an acceptor")
    acceptor_alt: float = Field(description="OfAltered probability that this position is an acceptor")
    acceptor: float = Field(description="Difference between Altered and Reference")

class DeltaScore(BaseModel):
    gene: str
    strand: Literal["+","-"]
    chr: str
    pos: int
    ref: str
    alt: str
    stats: list[Stats]

class BulkVarianstResponse(BaseModel):
    input: str = Field(description="Input variant formatted as chr-pos-ref-alt")
    scores: list[DeltaScore] | None = Field(description="Delta scores for a variant. Null if there is any error")
    error: str | None = Field(description="Error message if an error is encountered, otherwise Null")

@app.get("/")
def get_root():
    return {"App": "SpliceAI API"}

@app.get("/health/alive")
def get_alive():
    """
    Endpoint to check if the API is alive.

    Returns:
        dict: A dictionary with the status 'alive' to indicate the API is running.
    """
    return {"status": "alive"}

@app.get("/health/alive")
def get_alive():
    """
    Endpoint to check if the API is alive.

    Returns:
        dict: A dictionary with the status 'alive' to indicate the API is running.
    """
    return {"status": "alive"}

@app.get("/health/ready")
def get_ready():
    """
    Endpoint to check if the API is ready for handling requests.

    Returns:
        dict: A dictionary with the status 'ready' to indicate the API is ready to handle requests.
    """
    return {"status": "ready"}

@app.get("/get_annotations")
async def api_get_annotations():
    """
    API endpoint to get available annotations.

    Returns:
        dict: A dictionary of annotations available in the API.
    """
    return annotations

@app.get("/score_custom_seq/{sequence}")
async def api_score_custom_seq(sequence: str):
    """
    API endpoint to score a custom DNA sequence.

    This endpoint accepts a DNA sequence as part of the URL path and scores it using the `score_custom_sequence` function. The sequence must only contain the characters A, T, C, and G. If the sequence contains any other characters or is blank, the endpoint responds with a 400 status code and an error message.

    Parameters:
    - sequence (str): The DNA sequence to be scored. Must only contain A, T, C, and G.

    Returns:
    - On success, returns an array
    - On failure (if the sequence contains invalid characters or is blank), raises a DefaultException with status code 400 and a detailed error message.
    """
    if not dna_pattern.match(sequence):
        raise DefaultException(status_code=400, detail=jsonable_encoder(
            {'summary':'DNA string must contain ATCG',
             'details':f"Entered sequence must contain ATCG and not be blank"}))
    return score_custom_sequence(sequence=sequence, models=MODELS)


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
async def api_get_delta_scores(variant: SingleVariant) -> list[DeltaScore]:
    """
    Calculate SpliceAI delta scores for a specified single nucleotide variant.

    This endpoint receives a variant as input and computes the SpliceAI delta scores, which predict the effect of the variant on splicing. It leverages the SpliceAI algorithm to evaluate the potential impact on splice donor and acceptor sites, considering both the variant's genomic location and the specified genetic annotation (e.g., GRCh37 or GRCh38). The distance parameter specifies the maximum genomic distance (in base pairs) within which to assess potential splice site alterations, while the mask parameter allows for filtering specific types of splice site predictions. The process involves the annotation of the variant and calculation of delta scores to quantify changes in splicing efficiency.

    Parameters:
        variant (SingleVariant): A pydantic model instance that includes details about the chromosome (chrom), position (pos), reference allele (ref), alternative allele (alt), genetic annotation (annotation), and optional parameters for distance and mask.

    Returns:
        list[DeltaScore]: A list containing a DeltaScore object for the input variant, detailing the predicted changes in splicing efficiency due to the variant. Each DeltaScore object includes information about the gene affected, the strand, chromosomal location, reference and alternate alleles, and statistical measures detailing the predicted impact on splicing.

    Raises:
        DefaultException: If an error occurs during the calculation process, including issues with accessing annotation files or executing the SpliceAI algorithm, a DefaultException is raised with appropriate status code and error details.
    """
    record = Record(chrom=variant.chrom, pos=variant.pos, ref=variant.ref, alts=[variant.alt])

    annotation_file = None

    if variant.annotation in ['grch37','grch38']:
        annotation_file = variant.annotation
    else:
        annotation_file = files("spliceai_api.annotations").joinpath(f"{variant.annotation}.txt")

    try:
        ann = Annotator(os.getenv(annotations[variant.annotation]['fasta']), annotation_file)
        return get_delta_scores(record, ann, variant.distance, variant.mask, models=MODELS)
    except SpliceAIAPIException as e:
        raise DefaultException(status_code=400, detail=jsonable_encoder(
            {'summary':e.summary,
             'details':e.details}))
    except Exception as e:
        traceback.print_exc()
        raise DefaultException(status_code=500, detail=jsonable_encoder(
            {'summary':'Encountered error while calculating SpliceAI scores',
             'details':e.__doc__}))
    
@app.post("/get_bulk_delta_scores/")
async def api_get_bulk_delta_scores(variants: BulkVariantList) -> list[BulkVarianstResponse]:
    """
    API endpoint to calculate delta scores for a list of variants.

    Accepts a list of variants and their annotations to calculate SpliceAI delta scores in bulk. Each variant in the list is scored, and the response includes the input details and the calculated scores or an error message if applicable.

    Parameters:
    - variants (BulkVariantList): A list of variants along with annotation details.

    Returns:
    - A list of dictionaries, each containing the input variant details, calculated scores, and any error encountered during processing.
    """
    annotation_file = None

    if variants.annotation in ['grch37','grch38']:
        annotation_file = variants.annotation
    else:
        annotation_file = files("spliceai_api.annotations").joinpath(f"{variants.annotation}.txt")

    responses = []

    for variant in variants.variants:
        try:
            record = Record(chrom=variant.chrom, pos=variant.pos, ref=variant.ref, alts=[variant.alt])
            ann = Annotator(os.getenv(annotations[variants.annotation]['fasta']), annotation_file)

            input = f"{variant.chrom}-{variant.pos}-{variant.ref}-{variant.alt}"   
            scores = get_delta_scores(record, ann, variants.distance, variants.mask, models=MODELS)
            error = None
        
        except Exception as e:
            input = f"{variant.chrom}-{variant.pos}-{variant.ref}-{variant.alt}"   
            scores = None
            error = f"Error encountered: {str(e)}"
            
        response = {'input': input, 'scores': scores, 'error': error}
        responses.append(response)

    return responses