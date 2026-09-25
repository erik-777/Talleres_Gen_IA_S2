import csv
import json

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CATALOG_FILE, FAQ_FILE, POLICY_FILE


def load_policy_chunks():
    """política_devoluciones.md: texto libre -> se trocea de forma recursiva,
    respetando primero encabezados de sección y luego párrafos, para que cada
    chunk contenga una regla completa (ver Docs/taller2_fase2_base_conocimiento.md)."""
    text = POLICY_FILE.read_text(encoding="utf-8")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [
        Document(
            page_content=chunk,
            metadata={"source": "politica_devoluciones.md", "tipo": "politica"},
        )
        for chunk in chunks
    ]


def load_faq_chunks():
    """preguntas_frecuentes.json: cada FAQ ya es una unidad de sentido completa,
    así que cada registro se convierte en un único chunk (no se trocea por
    caracteres)."""
    faqs = json.loads(FAQ_FILE.read_text(encoding="utf-8"))
    documents = []
    for faq in faqs:
        content = f"Pregunta: {faq['pregunta']}\nRespuesta: {faq['respuesta']}"
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source": "preguntas_frecuentes.json",
                    "tipo": "faq",
                    "categoria": faq["categoria"],
                    "id": faq["id"],
                },
            )
        )
    return documents


def load_catalog_chunks():
    """catalogo_productos.csv: cada fila (producto) es una unidad de sentido
    completa, se serializa como una ficha de texto en lugar de vectorizar
    celdas sueltas."""
    documents = []
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            content = (
                f"Producto: {row['nombre']} | Categoría: {row['categoria']} | "
                f"Precio: ${row['precio_cop']} COP | Stock disponible: {row['stock']} "
                f"unidades | Descripción: {row['descripcion']}"
            )
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": "catalogo_productos.csv",
                        "tipo": "producto",
                        "sku": row["sku"],
                        "categoria": row["categoria"],
                    },
                )
            )
    return documents


def load_all_chunks():
    return load_policy_chunks() + load_faq_chunks() + load_catalog_chunks()
