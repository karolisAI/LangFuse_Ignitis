import os

from langfuse import Langfuse
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-local-tests"
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-local-tests"
os.environ["LANGFUSE_BASE_URL"] = "http://127.0.0.1:1"
exporter = InMemorySpanExporter()
client = Langfuse(span_exporter=exporter, should_export_span=lambda span: True)
