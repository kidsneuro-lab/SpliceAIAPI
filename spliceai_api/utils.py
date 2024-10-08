from dataclasses import dataclass
import yaml
import logging, os
from importlib.resources import files

from spliceai_api.exceptions import SpliceAIAPIException
from spliceai_api import ENSEMBL_TIMEOUT

from pyfaidx import Fasta
import requests
from keras.models import load_model
from pkg_resources import resource_filename
from spliceai.utils import one_hot_encode, normalise_chrom
import numpy as np
import pandas as pd

from spliceai_api import MODELS

logger = logging.getLogger(__name__)

@dataclass
class Record:
    chrom: str = None
    pos: int = None
    ref: str = None
    alts: list = None

class Annotator:

    def __init__(self, ref_fasta, annotations):

        if annotations == 'grch37':
            annotations = resource_filename(__name__, 'annotations/grch37.txt')
        elif annotations == 'grch38':
            annotations = resource_filename(__name__, 'annotations/grch38.txt')

        try:
            df = pd.read_csv(annotations, sep='\t', dtype={'CHROM': object})
            self.genes = df['#NAME'].to_numpy()
            self.chroms = df['CHROM'].to_numpy()
            self.strands = df['STRAND'].to_numpy()
            self.tx_starts = df['TX_START'].to_numpy()+1
            self.tx_ends = df['TX_END'].to_numpy()
            self.exon_starts = [np.asarray([int(i) for i in c.split(',') if i])+1
                                for c in df['EXON_START'].to_numpy()]
            self.exon_ends = [np.asarray([int(i) for i in c.split(',') if i])
                              for c in df['EXON_END'].to_numpy()]
        except IOError as e:
            logging.error('{}'.format(e))
            exit()
        except (KeyError, pd.errors.ParserError) as e:
            logging.error('Gene annotation file {} not formatted properly: {}'.format(annotations, e))
            exit()

        try:
            self.ref_fasta = Fasta(ref_fasta, rebuild=False)
        except IOError as e:
            logging.error('{}'.format(e))
            exit()

    def get_name_and_strand(self, chrom, pos):

        chrom = normalise_chrom(chrom, list(self.chroms)[0])
        idxs = np.intersect1d(np.nonzero(self.chroms == chrom)[0],
                              np.intersect1d(np.nonzero(self.tx_starts <= pos)[0],
                              np.nonzero(pos <= self.tx_ends)[0]))

        if len(idxs) >= 1:
            return self.genes[idxs], self.strands[idxs], idxs
        else:
            return [], [], []

    def get_pos_data(self, idx, pos):

        dist_tx_start = self.tx_starts[idx]-pos
        dist_tx_end = self.tx_ends[idx]-pos
        dist_exon_bdry = min(np.union1d(self.exon_starts[idx], self.exon_ends[idx])-pos, key=abs)
        dist_ann = (dist_tx_start, dist_tx_end, dist_exon_bdry)

        return dist_ann

def load_annotations() -> dict:
    logger.debug("Loading annotations")
    annotation_config = files("spliceai_api.annotations").joinpath("annotations.yml")

    with open(annotation_config, "r") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise SpliceAIAPIException("Unable to load annotations file")

def validate_fasta(assemblies: list):
    for assembly in assemblies:
        if os.getenv(assembly) == None:
            raise SpliceAIAPIException("Genomic reference not found", f"FASTA file for {assembly} assembly not defined")
        elif not os.path.exists(os.getenv(assembly)):
            raise SpliceAIAPIException("Genomic reference not found", f"FASTA file for {assembly}: {os.getenv(assembly)} not found")
 
def score_custom_sequence(sequence: str, models: list) -> dict:
    logger.debug(f"Scoring sequence: {sequence}")
    context = 10000
    x = one_hot_encode('N'*(context//2) + sequence + 'N'*(context//2))[None, :]
    y = np.mean([models[m].predict(x) for m in range(5)], axis=0)

    return {
        'acceptor_prob': y[0, :, 1].tolist(),
        'donor_prob': y[0, :, 2].tolist()
    }

def ensembl_get_genomic_coord(variant: str, assembly: str = 'grch38') -> dict:
    logger.debug(f"Obtaining genomic position for variant: {variant}, assembly: {assembly}")
    server = 'https://grch37.rest.ensembl.org' if assembly=='grch37' else 'https://rest.ensembl.org'
    ext = f"/variant_recoder/human/{variant}?fields=None&vcf_string=1"
    logger.debug(f"Ensembl URL: {server}{ext}")

    resp = requests.get(server+ext, headers={ "Content-Type" : "application/json"}, timeout=float(ENSEMBL_TIMEOUT))
    if not resp.ok:
        resp.raise_for_status()

    resp_json = resp.json()

    chrom, pos, ref, alt = resp_json[0][list(resp_json[0].keys())[0]]['vcf_string'][0].split('-')

    return({
        'chr': chrom,
        'pos': pos,
        'ref': ref,
        'alt': alt
    })

def get_delta_scores(record, ann, dist_var, mask, models):

    cov = 2*dist_var+1
    wid = 10000+cov
    delta_scores = []
    spliceai_variant_records = []

    try:
        record.chrom, record.pos, record.ref, len(record.alts)
    except TypeError:
        logging.error('Skipping record (bad input): {}'.format(record))
        raise SpliceAIAPIException('Skipping record (bad input): {}'.format(record))

    (genes, strands, idxs) = ann.get_name_and_strand(record.chrom, record.pos)
    if len(idxs) == 0:
        logging.warning("No gene annotations found for given location")
        raise SpliceAIAPIException('No gene annotations found for given location: {}'.format(record))

    chrom = normalise_chrom(record.chrom, list(ann.ref_fasta.keys())[0])
    try:
        seq = ann.ref_fasta[chrom][record.pos-wid//2-1:record.pos+wid//2].seq
    except KeyError as e:
        logging.error(f"Encountered error: {str(e)}")
        raise SpliceAIAPIException('Encountered error: {}'.format(str(e)))
    except (IndexError, ValueError):
        logging.warning('Skipping record (fasta issue): {}'.format(record))
        raise SpliceAIAPIException('Skipping record (fasta issue): {}'.format(record))

    if seq[wid//2:wid//2+len(record.ref)].upper() != record.ref:
        logging.warning('Skipping record (ref issue): {}'.format(record))
        raise SpliceAIAPIException('Skipping record (ref issue): {}'.format(record))

    if len(seq) != wid:
        logging.warning('Skipping record (near chromosome end): {}'.format(record))
        raise SpliceAIAPIException('Skipping record (near chromosome end): {}'.format(record))

    if len(record.ref) > 2*dist_var:
        logging.warning('Skipping record (ref too long): {}'.format(record))
        raise SpliceAIAPIException('Skipping record (ref too long): {}'.format(record))

    spliceai_stats = []

    for j in range(len(record.alts)):
        for i in range(len(idxs)):

            if '.' in record.alts[j] or '-' in record.alts[j] or '*' in record.alts[j]:
                continue

            if '<' in record.alts[j] or '>' in record.alts[j]:
                continue

            if len(record.ref) > 1 and len(record.alts[j]) > 1:
                delta_scores.append("{}|{}|.|.|.|.|.|.|.|.".format(record.alts[j], genes[i]))
                continue

            dist_ann = ann.get_pos_data(idxs[i], record.pos)
            pad_size = [max(wid//2+dist_ann[0], 0), max(wid//2-dist_ann[1], 0)]
            ref_len = len(record.ref)
            alt_len = len(record.alts[j])
            del_len = max(ref_len-alt_len, 0)

            x_ref = 'N'*pad_size[0]+seq[pad_size[0]:wid-pad_size[1]]+'N'*pad_size[1]
            x_alt = x_ref[:wid//2]+str(record.alts[j])+x_ref[wid//2+ref_len:]

            x_ref = one_hot_encode(x_ref)[None, :]
            x_alt = one_hot_encode(x_alt)[None, :]

            if strands[i] == '-':
                x_ref = x_ref[:, ::-1, ::-1]
                x_alt = x_alt[:, ::-1, ::-1]

            y_ref = np.mean([models[m].predict(x_ref) for m in range(5)], axis=0)
            y_alt = np.mean([models[m].predict(x_alt) for m in range(5)], axis=0)

            if strands[i] == '-':
                y_ref = y_ref[:, ::-1]
                y_alt = y_alt[:, ::-1]

            if ref_len > 1 and alt_len == 1:
                y_alt = np.concatenate([
                    y_alt[:, :cov//2+alt_len],
                    np.zeros((1, del_len, 3)),
                    y_alt[:, cov//2+alt_len:]],
                    axis=1)
            elif ref_len == 1 and alt_len > 1:
                y_alt = np.concatenate([
                    y_alt[:, :cov//2],
                    np.max(y_alt[:, cov//2:cov//2+alt_len], axis=1)[:, None, :],
                    y_alt[:, cov//2+alt_len:]],
                    axis=1)

            y = np.concatenate([y_ref, y_alt])

            idx_pa = (y[1, :, 1]-y[0, :, 1]).argmax()
            idx_na = (y[0, :, 1]-y[1, :, 1]).argmax()
            idx_pd = (y[1, :, 2]-y[0, :, 2]).argmax()
            idx_nd = (y[0, :, 2]-y[1, :, 2]).argmax()

            mask_pa = np.logical_and((idx_pa-cov//2 == dist_ann[2]), mask)
            mask_na = np.logical_and((idx_na-cov//2 != dist_ann[2]), mask)
            mask_pd = np.logical_and((idx_pd-cov//2 == dist_ann[2]), mask)
            mask_nd = np.logical_and((idx_nd-cov//2 != dist_ann[2]), mask)

            delta_scores.append("{}|{}|{:.2f}|{:.2f}|{:.2f}|{:.2f}|{}|{}|{}|{}|{:.2f}|{:.2f}|{:.2f}|{:.2f}|{:.2f}|{:.2f}|{:.2f}|{:.2f}".format(
                                record.alts[j],
                                genes[i],
                                (y[1, idx_pa, 1]-y[0, idx_pa, 1])*(1-mask_pa),
                                (y[0, idx_na, 1]-y[1, idx_na, 1])*(1-mask_na),
                                (y[1, idx_pd, 2]-y[0, idx_pd, 2])*(1-mask_pd),
                                (y[0, idx_nd, 2]-y[1, idx_nd, 2])*(1-mask_nd),
                                idx_pa-cov//2,
                                idx_na-cov//2,
                                idx_pd-cov//2,
                                idx_nd-cov//2,
                                y[0, idx_pa, 1],
                                y[1, idx_pa, 1],
                                y[0, idx_na, 1],
                                y[1, idx_na, 1],
                                y[0, idx_pd, 2],
                                y[1, idx_pd, 2],
                                y[0, idx_nd, 2],
                                y[1, idx_nd, 2]))

            dist_from_variant = np.arange(-1 * dist_var, 0).tolist()
            dist_from_variant.extend(np.arange(0, dist_var + 1).tolist())

            donor = (y_alt[0, :, 2] - y_ref[0, :, 2]).tolist()
            donor_ref = y_ref[0, :, 2].tolist()
            donor_alt = y_alt[0, :, 2].tolist()
            acceptor = (y_alt[0, :, 1] - y_ref[0, :, 1]).tolist()
            acceptor_ref = y_ref[0, :, 1].tolist()
            acceptor_alt = y_alt[0, :, 1].tolist()

            spliceai_variant_record = {}
            spliceai_stats = []

            for index in np.arange(0, len(dist_from_variant)):
                stat_record = {
                    'dist_from_variant': dist_from_variant[index],
                    'donor_ref': donor_ref[index],
                    'donor_alt': donor_alt[index],
                    'donor': donor[index],
                    'acceptor_ref': acceptor_ref[index],
                    'acceptor_alt': acceptor_alt[index],
                    'acceptor': acceptor[index]
                }

                spliceai_stats.append(stat_record)

            spliceai_variant_record['gene'] = genes[i]
            spliceai_variant_record['strand'] = strands[i]
            spliceai_variant_record['chr'] = record.chrom
            spliceai_variant_record['pos'] = record.pos
            spliceai_variant_record['ref'] = record.ref
            spliceai_variant_record['alt'] = record.alts[j]
            spliceai_variant_record['stats'] = spliceai_stats

            spliceai_variant_records.append(spliceai_variant_record)

    return spliceai_variant_records