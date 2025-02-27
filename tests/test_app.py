import pytest

from fastapi.testclient import TestClient

from spliceai_api.app import app

client = TestClient(app)

data = [
    ('valid_sequence', {'seq':'ATACATACATACATACATACATACATACATACATACATACATACATACATACATACATACATAC'}, 200),
    ('invalid_sequence', {'seq':'XYAX'}, 422),
    ('invalid_sequence', {'seq':'XYAXXYAXXYAXXYAXXYAXXYAXXYAXXYAXXYAXXYAXXYAXXYAXXYAXXYAXXYAXXYAX'}, 400)
]

variants = [
    ('valid_hgvsc', 'NM_005502:c.66+5G>C', 'grch38_custom', 200, {'chr': '9', 'pos': '104903609', 'ref': 'C', 'alt': 'G'}),
    ('invalid_hgvsc', 'NM_005502:c.+5G>C', 'grch38_custom', 400, None),
    ('invalid_assembly', 'NM_005502.3:c.+5G>C', 'grch99', 400, None)
]

variants_for_spliceai = [
    ('valid', {'chr': '21', 'pos': 26840275, 'ref': 'C', 'alt': 'A'}, 'grch38_custom', 50, 0, 200),
    ('invalid_chromosome', {'chr': '1', 'pos': 26840275, 'ref': 'G', 'alt': 'A'}, 'grch38_custom', 50, 0, 400),
    ('invalid_chromosome', {'chr': '1', 'pos': 26840275, 'ref': 'G', 'alt': 'A'}, 'grch38_custom', 50, 0, 400),
    ('invalid_assembly', {'chr': '21', 'pos': 26840275, 'ref': 'G', 'alt': 'A'}, 'grch22', 50, 0, 422)
]

def idfn(test_data):
    ids = [values[0] for values in test_data]
    return ids

@pytest.mark.parametrize("id,input,response_code", data, ids=idfn(data))
def test_score_custom_seq(id, input, response_code):
    response = client.post(f"/score_custom_seq/", json=input)
    assert response.status_code == response_code

@pytest.mark.parametrize("id,input,assembly,response_code,genomic", variants, ids=idfn(variants))
def test_get_genomic_coord(id, input, assembly, response_code, genomic):
    response = client.get(f"/get_genomic_coord/{assembly}/{input}")
    assert response.status_code == response_code
    if response.status_code == 200:
        assert response.json() == genomic

@pytest.mark.parametrize("id,genomic,annotation,distance,mask,response_code", variants_for_spliceai, ids=idfn(variants_for_spliceai))
def test_get_delta_scores(id, genomic, annotation, distance, mask, response_code):
    data = {
                'chrom': genomic['chr'], 
                'pos': genomic['pos'],
                'ref': genomic['ref'],
                'alt': genomic['alt'],
                'annotation': annotation,
                'distance': distance,
                'mask': mask
            }
    response = client.post('/get_delta_scores/', json=data)
    assert response.status_code == response_code
    if response.status_code == 200:
        assert len(response.json()) >= 1

def test_get_bulk_delta_scores():
    data = {
                "annotation": "grch38",
                "mask": 0,
                "distance": 50,
                "variants": [
                    {
                        "chrom": "21",
                        "pos": 32657714,
                        "ref": "A",
                        "alt": "G"
                    },
                    {
                        "chrom": "21",
                        "pos": 32695049,
                        "ref": "A",
                        "alt": "G"
                    }
                ]
            }
    response = client.post('/get_bulk_delta_scores/', json=data)
    assert response.status_code == 200
    if response.status_code == 200:
        assert len(response.json()) == 2