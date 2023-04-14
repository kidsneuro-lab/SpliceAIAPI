import os, sys

basedir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(basedir, "..")) 

os.environ['GRCH38_FASTA'] = os.path.join(basedir, 'data', 'chr21.fa')
os.environ['GRCH37_FASTA'] = os.path.join(basedir, 'data', 'chr21.fa')
os.environ['ENSEMBL_TIMEOUT'] = '60'