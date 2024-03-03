FROM python:3.10-slim
COPY ./hg_ref /hg_ref

RUN apt-get update \
  && apt-get install -y \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /

RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir -r /requirements.txt

# Add a new user "nonrootuser" with user id 8877
RUN useradd -u 8877 nonrootuser

COPY . /app
WORKDIR /app

ENV GRCH37_FASTA=hg_ref/Homo_sapiens_assembly19.fasta.gz
ENV GRCH38_FASTA=hg_ref/Homo_sapiens_assembly38.fasta.gz

EXPOSE 5001

CMD ["uvicorn", "spliceai_api.app:app", "--host", "0.0.0.0", "--port", "5001", "--root-path", "/spliceai/api/v1"]
