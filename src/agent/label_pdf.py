"""Etiqueta de devolución en PDF (simula el documento que imprimiría el cliente)."""

from fpdf import FPDF

from agent_config import SIMULATED_TODAY

GREEN = (46, 125, 50)
GRAY = (90, 90, 90)


def _row(pdf, label, value):
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*GRAY)
    pdf.cell(55, 7, label)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 7, str(value), align="L", new_x="LMARGIN", new_y="NEXT")


def render_label_pdf(label, customer_name, product, motivo):
    pdf = FPDF(format=(148, 210))  # A5 en mm
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_fill_color(*GREEN)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "  EcoMarket - Etiqueta de devolución", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, label["codigo_devolucion"], new_x="LMARGIN", new_y="NEXT")
    pdf.code39(f"*{label['guia_transportadora']}*", x=pdf.l_margin, y=pdf.get_y() + 1, w=0.6, h=14)
    pdf.set_y(pdf.get_y() + 17)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Guía {label['transportadora']}: {label['guia_transportadora']}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    _row(pdf, "Remitente", customer_name)
    _row(pdf, "Destinatario", label["direccion_bodega"])
    _row(pdf, "Pedido", label["numero_pedido"])
    _row(pdf, "Producto", product)
    _row(pdf, "Motivo", motivo)
    _row(pdf, "Fecha de emisión", SIMULATED_TODAY.isoformat())
    _row(pdf, "Enviar antes de", label["fecha_limite_envio"])
    _row(pdf, "Costo del envío", f"Lo asume {label['costo_envio_retorno']}")
    _row(pdf, "Reembolso", label["reembolso"])

    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 4, "Imprime esta etiqueta y pégala en el paquete. Documento generado por el "
                         "asistente virtual de EcoMarket (proyecto académico, datos simulados).")
    return bytes(pdf.output())
