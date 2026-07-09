from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, time
from pathlib import Path
from typing import Literal

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


Decision = Literal["em_branco", "aprovado", "reprovado"]
Evaluation = Literal["em_branco", "adequado", "inadequado"]


MESES = [
    "",
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]

DIAS = {
    1: "primeiro",
    2: "segundo",
    3: "terceiro",
    4: "quarto",
    5: "quinto",
    6: "sexto",
    7: "sétimo",
    8: "oitavo",
    9: "nono",
    10: "décimo",
    11: "décimo primeiro",
    12: "décimo segundo",
    13: "décimo terceiro",
    14: "décimo quarto",
    15: "décimo quinto",
    16: "décimo sexto",
    17: "décimo sétimo",
    18: "décimo oitavo",
    19: "décimo nono",
    20: "vigésimo",
    21: "vigésimo primeiro",
    22: "vigésimo segundo",
    23: "vigésimo terceiro",
    24: "vigésimo quarto",
    25: "vigésimo quinto",
    26: "vigésimo sexto",
    27: "vigésimo sétimo",
    28: "vigésimo oitavo",
    29: "vigésimo nono",
    30: "trigésimo",
    31: "trigésimo primeiro",
}


@dataclass
class Examiner:
    name: str
    title: str = "Prof. Dr."
    institution: str = "UFPA"
    role: str = "membro titular"
    signature_name: str = ""
    evaluation: dict[str, Evaluation] = field(default_factory=dict)
    comments: str = ""

    @property
    def display_name(self) -> str:
        return self.name.strip().upper()

    @property
    def signed_name(self) -> str:
        return self.signature_name.strip() or self.name.strip()

    @property
    def title_name(self) -> str:
        title = self.title.strip()
        return f"{title} {self.name.strip()}".strip()


@dataclass
class DefenseData:
    student_name: str
    advisor_name: str
    title: str
    defense_date: date
    defense_time: time
    location: str
    program: str = "Programa de Pós-graduação em Neurociências e Biologia Celular"
    institute: str = "Instituto de Ciências Biológicas"
    university: str = "Universidade Federal do Pará"
    course_level: str = "Mestrado"
    document_kind: str = "Qualificação"
    work_kind: str = "dissertação"
    student_gender: str = "discente"
    advisor_title: str = "Prof. Dr."
    president: Examiner | None = None
    examiners: list[Examiner] = field(default_factory=list)
    substitutes: list[Examiner] = field(default_factory=list)
    decision: Decision = "em_branco"


EVAL_ITEMS = [
    "Domínio e conhecimento do trabalho",
    "Planejamento experimental e resultados",
    "Pesquisa e organização bibliográfica",
    "Exposição e defesa do trabalho",
]


def date_long(d: date) -> str:
    return f"{d.day:02d} de {MESES[d.month]} de {d.year}"


def date_long_text(d: date) -> str:
    return f"{DIAS[d.day]} dia do mês de {MESES[d.month]} do ano de {d.year}"


def time_text(t: time) -> str:
    if t.minute:
        return f"{t.hour} h {t.minute:02d} min"
    return f"{t.hour} h"


def time_long_text(t: time) -> str:
    horas = {
        0: "zero horas",
        1: "uma hora",
        2: "duas horas",
        3: "três horas",
        4: "quatro horas",
        5: "cinco horas",
        6: "seis horas",
        7: "sete horas",
        8: "oito horas",
        9: "nove horas",
        10: "dez horas",
        11: "onze horas",
        12: "doze horas",
        13: "treze horas",
        14: "quatorze horas",
        15: "quinze horas",
        16: "dezesseis horas",
        17: "dezessete horas",
        18: "dezoito horas",
        19: "dezenove horas",
        20: "vinte horas",
        21: "vinte e uma horas",
        22: "vinte e duas horas",
        23: "vinte e três horas",
    }
    if t.minute == 0:
        return horas[t.hour]
    if t.minute == 30:
        return f"{horas[t.hour]} e trinta minutos"
    return f"{horas[t.hour]} e {t.minute:02d} minutos"


def safe_filename(value: str) -> str:
    value = re.sub(r"[^\w\s.-]", "", value, flags=re.UNICODE).strip().lower()
    value = re.sub(r"\s+", "_", value)
    return value[:90] or "documento"


class SignatureLine(Flowable):
    def __init__(self, name: str, width: float = 7.0 * cm):
        super().__init__()
        self.name = name
        self.width = width

    def wrap(self, avail_width, avail_height):
        return self.width, 1.45 * cm

    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(colors.black)
        self.canv.setLineWidth(0.7)
        self.canv.line(0, 0.76 * cm, self.width, 0.76 * cm)
        self.canv.setFont("Times-Roman", 10)
        self.canv.drawCentredString(self.width / 2, 0.38 * cm, self.name)
        self.canv.restoreState()


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "Header",
            parent=styles["Normal"],
            fontName="Times-Roman",
            fontSize=11,
            leading=13,
            alignment=TA_CENTER,
            spaceAfter=1,
        )
    )
    styles.add(
        ParagraphStyle(
            "TitleFormal",
            parent=styles["Normal"],
            fontName="Times-Bold",
            fontSize=12,
            leading=15,
            alignment=TA_CENTER,
            spaceBefore=18,
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            "BodyFormal",
            parent=styles["Normal"],
            fontName="Times-Roman",
            fontSize=11.5,
            leading=17,
            firstLineIndent=1.25 * cm,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            "Label",
            parent=styles["Normal"],
            fontName="Times-Bold",
            fontSize=11.5,
            leading=15,
            alignment=TA_LEFT,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            "Value",
            parent=styles["Normal"],
            fontName="Times-Roman",
            fontSize=11.5,
            leading=15,
            alignment=TA_LEFT,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            "Small",
            parent=styles["Normal"],
            fontName="Times-Roman",
            fontSize=9.5,
            leading=12,
            alignment=TA_LEFT,
        )
    )
    return styles


S = _styles()


def p(text: str, style: str = "BodyFormal") -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), S[style])


def _doc(buffer: io.BytesIO) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2.3 * cm,
        leftMargin=2.3 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.8 * cm,
    )


def _draw_page_number(canvas: Canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 9)
    canvas.drawRightString(A4[0] - 2.3 * cm, 1.1 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _header(data: DefenseData) -> list:
    return [
        p(data.university, "Header"),
        p(data.institute, "Header"),
        p(data.program, "Header"),
    ]


def _decision_marks(decision: Decision) -> str:
    aprovar = "X" if decision == "aprovado" else " "
    reprovar = "X" if decision == "reprovado" else " "
    return f"( {aprovar} ) APROVAR&nbsp;&nbsp;&nbsp;( {reprovar} ) REPROVAR"


def _examiner_list(data: DefenseData) -> str:
    parts = []
    if data.president:
        parts.append(
            f"{data.president.title_name.upper()} ({data.president.institution}), na condição de Presidente (sem direito a voto)"
        )
    for ex in data.examiners:
        title = _short_academic_title(ex.title)
        parts.append(f"{title} {ex.display_name} ({ex.institution}), na condição de {ex.role}")
    for ex in data.substitutes:
        title = _short_academic_title(ex.title)
        parts.append(f"{title} {ex.display_name} ({ex.institution}), na condição de {ex.role}")
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + ", e " + parts[-1]


def _short_academic_title(title: str) -> str:
    normalized = title.strip().lower()
    if "dra" in normalized:
        return "Dra."
    if "dr" in normalized:
        return "Dr."
    if "profa" in normalized:
        return "Profa."
    if "prof" in normalized:
        return "Prof."
    return title.strip()


def generate_ata_pdf(data: DefenseData) -> bytes:
    buffer = io.BytesIO()
    story = _header(data)
    title = (
        f"ATA DA COMISSÃO EXAMINADORA DA {data.document_kind.upper()} DE "
        f"{data.course_level.upper()} EM NEUROCIÊNCIAS E BIOLOGIA CELULAR "
        f"APRESENTADO E DEFENDIDO PELA {data.student_gender.upper()} "
        f"{data.student_name.upper()}"
    )
    story += [Spacer(1, 0.25 * cm), p(title, "TitleFormal")]

    president = data.president or Examiner(name=data.advisor_name, title=data.advisor_title)
    data.president = president
    banca = _examiner_list(data)
    body = (
        f"No {date_long_text(data.defense_date)}, às {time_long_text(data.defense_time)}, "
        f"reuniu-se de forma remota e síncrona na {data.location}, a comissão examinadora "
        f"para avaliar o trabalho apresentado e defendido pela {data.student_gender} de "
        f"{data.course_level.lower()} {data.student_name.upper()} e intitulado: "
        f"“{data.title.upper()}” orientada pelo {data.advisor_title} {data.advisor_name.upper()}. "
        f"A comissão examinadora, organizada obedecendo ao disposto nas Resoluções do Conselho "
        f"Superior de Ensino e Pós-Graduação, foi constituída pelos docentes: {banca}. "
        f"Após apresentação e arguição individual por cada membro titular, a comissão examinadora "
        f"decidiu, por unanimidade, {_decision_marks(data.decision)} a {data.student_gender} em "
        f"sua {data.work_kind} de {data.course_level.lower()}. Nada mais havendo a tratar, "
        f"o presidente da comissão examinadora deu por encerrado os trabalhos e foi lavrada a "
        f"presente ata e assinada por todos os membros da comissão examinadora."
    )
    story.append(p(body))
    story.append(Spacer(1, 0.4 * cm))

    signers = [president] + data.examiners
    rows = []
    for idx in range(0, len(signers), 2):
        row = [SignatureLine(signers[idx].signed_name.upper())]
        if idx + 1 < len(signers):
            row.append(SignatureLine(signers[idx + 1].signed_name.upper()))
        else:
            row.append("")
        rows.append(row)
    story.append(
        Table(
            rows,
            colWidths=[7.2 * cm, 7.2 * cm],
            style=TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        )
    )
    _doc(buffer).build(story, onFirstPage=_draw_page_number, onLaterPages=_draw_page_number)
    return buffer.getvalue()


def _checkbox(label: str, state: Evaluation) -> str:
    return f"( {'X' if state == label else ' '} )"


def generate_ficha_pdf(data: DefenseData, examiner: Examiner) -> bytes:
    buffer = io.BytesIO()
    story = _header(data)
    story += [
        Spacer(1, 0.35 * cm),
        p(f"FICHA DE AVALIAÇÃO - DEFESA DE {data.work_kind.upper()} DE {data.course_level.upper()} - PPGNBC", "TitleFormal"),
        p("Título da dissertação:", "Label"),
        p(data.title.upper(), "Value"),
        Spacer(1, 0.1 * cm),
        p(f"<b>Discente:</b> {data.student_name.upper()}", "Value"),
        p(f"<b>Docente:</b> {data.advisor_title.upper()} {data.advisor_name.upper()}", "Value"),
        Spacer(1, 0.1 * cm),
        p(f"<b>Local da defesa:</b> {data.location}", "Value"),
        p(f"<b>Data da defesa:</b> {date_long(data.defense_date)}", "Value"),
        p(f"<b>Horário da defesa:</b> {time_text(data.defense_time)}", "Value"),
        Spacer(1, 0.2 * cm),
        p("ITENS DA AVALIAÇÃO", "Label"),
    ]

    rows = [[p("<b>Item</b>", "Small"), p("<b>Adequado</b>", "Small"), p("<b>Inadequado</b>", "Small")]]
    for item in EVAL_ITEMS:
        state = examiner.evaluation.get(item, "em_branco")
        rows.append([p(item, "Small"), p(_checkbox("adequado", state), "Small"), p(_checkbox("inadequado", state), "Small")])
    story.append(
        Table(
            rows,
            colWidths=[10.2 * cm, 2.3 * cm, 2.8 * cm],
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        )
    )
    story += [
        Spacer(1, 0.45 * cm),
        p("OBSERVAÇÕES E COMENTÁRIOS", "Label"),
        p("(Obrigatório o preenchimento quando existirem julgados como inadequados)", "Small"),
    ]
    comments = examiner.comments.strip()
    if comments:
        story.append(p(comments, "Value"))
    else:
        blank_rows = [[""], [""], [""], [""]]
        story.append(
            Table(
                blank_rows,
                colWidths=[15.3 * cm],
                rowHeights=[0.8 * cm] * 4,
                style=TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#AAAAAA")),
                    ]
                ),
            )
        )
    story += [
        Spacer(1, 1.25 * cm),
        Table(
            [[SignatureLine(examiner.signed_name, 8.2 * cm)]],
            colWidths=[15.3 * cm],
            style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]),
        ),
        p(examiner.institution, "Header"),
    ]
    _doc(buffer).build(story, onFirstPage=_draw_page_number, onLaterPages=_draw_page_number)
    return buffer.getvalue()


def generate_zip(data: DefenseData, include_ata: bool = True, include_fichas: bool = True) -> bytes:
    buffer = io.BytesIO()
    stem = safe_filename(data.student_name)
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if include_ata:
            zf.writestr(f"ata_{stem}.pdf", generate_ata_pdf(data))
        if include_fichas:
            for idx, examiner in enumerate(data.examiners, start=1):
                zf.writestr(f"ficha_avaliador_{idx}_{safe_filename(examiner.name)}.pdf", generate_ficha_pdf(data, examiner))
    return buffer.getvalue()


def save_sample(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    data = DefenseData(
        student_name="João David Monteiro Costa",
        advisor_name="Givago da Silva Souza",
        title="Influência do tamanho do estímulo e da duração do ciclo no julgamento de uniformidade da velocidade angular de movimentos elípticos",
        defense_date=date(2026, 7, 9),
        defense_time=time(18, 30),
        location="Sala Virtual https://meet.google.com/dec-tnmf-rnv",
        president=Examiner("Givago da Silva Souza", "Prof. Dr.", "UFPA", "Presidente"),
        examiners=[
            Examiner("Bianca Callegari", "Profa. Dra.", "UFPA"),
            Examiner("Bruna Rafaela da Silva Sousa", "Profa. Dra.", "UFPA"),
            Examiner("Railson Cruz Salomão", "Prof. Dr.", "UFPA"),
        ],
        substitutes=[Examiner("Letícima Miquilini de Arruda Farias", "Profa. Dra.", "UFPA", "membro suplente")],
    )
    path = output_dir / "documentos_banca_exemplo.zip"
    path.write_bytes(generate_zip(data))
    return path
