FROM python:3.12-slim
# Cluster nodes are qemu64: numpy>=2.4 wheels do not import there.
RUN pip install --no-cache-dir "numpy<2.4" h5py matplotlib && apt-get update -qq && apt-get install -y -qq --no-install-recommends unzip zip && rm -rf /var/lib/apt/lists/*
COPY derive_behaviour.py make_trace_pages.py /usr/local/bin/
ENTRYPOINT ["python", "/usr/local/bin/derive_behaviour.py"]
