import pytest

from fastapi.testclient import TestClient

from spliceai_api.app import app

client = TestClient(app)

data = [
    ('valid_sequence', 'ATCG', 200),
    ('invalid_sequence', 'XYAX', 400)
]

variants_for_spliceai = [
    ('valid', {'chr': '21', 'pos': 26840275, 'ref': 'C', 'alt': 'A'}, 'grch38', 50, 0, 200),
    ('invalid_chromosome', {'chr': '1', 'pos': 26840275, 'ref': 'G', 'alt': 'A'}, 'grch38', 50, 0, 400),
    ('invalid_chromosome', {'chr': '1', 'pos': 26840275, 'ref': 'G', 'alt': 'A'}, 'grch38_custom', 50, 0, 400),
    ('invalid_assembly', {'chr': '21', 'pos': 26840275, 'ref': 'G', 'alt': 'A'}, 'grch22', 50, 0, 422)
]

def idfn(test_data):
    ids = [values[0] for values in test_data]
    return ids

@pytest.mark.parametrize("id,input,response_code", data, ids=idfn(data))
def test_score_custom_seq(id, input, response_code):
    response = client.get(f"/score_custom_seq/{input}")
    assert response.status_code == response_code

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