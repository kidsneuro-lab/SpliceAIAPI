import os

# Check for ENSEMBL_TIMEOUT environment variable
ENSEMBL_TIMEOUT = os.getenv("ENSEMBL_TIMEOUT")
if ENSEMBL_TIMEOUT is None:
    raise EnvironmentError("Environment variable 'ENSEMBL_TIMEOUT' is not declared. Please set this variable before running the application.")
