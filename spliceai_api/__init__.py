import logging
import os

from keras.models import load_model
from pkg_resources import resource_filename

# Check for ENSEMBL_TIMEOUT environment variable
ENSEMBL_TIMEOUT = os.getenv("ENSEMBL_TIMEOUT")
if ENSEMBL_TIMEOUT is None:
    raise EnvironmentError("Environment variable 'ENSEMBL_TIMEOUT' is not declared. Please set this variable before running the application.")

logging.info("Loading SpliceAI models during start up")
paths = ('models/spliceai{}.h5'.format(x) for x in range(1, 6))
MODELS = [load_model(resource_filename('spliceai', x)) for x in paths]