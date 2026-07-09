from __future__ import annotations

from datetime import date, time

import pandas as pd
import streamlit as st

from document_generator import DefenseData, EVAL_ITEMS, Examiner, generate_ata_pdf, generate_ficha_pdf, generate_zip


st.set_page_config(page_title="Gerador de atas e fichas - PPGNBC", layout="wide")

st.title("Gerador de ata e fichas de avaliação")
st.caption("Rotina para gerar PDFs a partir dos dados da defesa/qualificação.")


def default_examiners() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Nome": "Avaliador 1", "Título": "Profa. Dra.", "Instituição": "UFPA", "Função": "membro titular"},
            {"Nome": "Avaliador 2", "Título": "Profa. Dra.", "Instituição": "UFPA", "Função": "membro titular"},
            {"Nome": "Avaliador 3", "Título": "Prof. Dr.", "Instituição": "UFPA", "Função": "membro titular"},
        ]
    )


with st.sidebar:
    st.header("Dados gerais")
    document_kind = st.selectbox("Tipo de banca", ["Qualificação", "Defesa"], index=0)
    course_level = st.selectbox("Nível", ["Mestrado", "Doutorado"], index=0)
    work_kind = st.selectbox("Tipo de trabalho", ["dissertação", "tese", "qualificação"], index=0)
    student_gender = st.selectbox("Tratamento do discente", ["discente", "mestrando", "mestranda", "doutorando", "doutoranda"], index=0)
    decision = st.selectbox("Resultado na ata", ["em_branco", "aprovado", "reprovado"], index=0)

    st.header("Cabeçalho institucional")
    university = st.text_input("Universidade", "Universidade Federal do Pará")
    institute = st.selectbox("Indique a sub-unidade", ["Instituto de Ciências Biológicas","Núcleo de Medicina Tropical"],index=0)
    program = st.selectbox("Indique o Programa", ["Programa de Pós-graduação em Neurociências e Biologia Celular","Programa de Pós-graduação em Saúde na Amazônia"],index=0)

left, right = st.columns([1.15, 1])

with left:
    st.subheader("Dados da sessão pública")
    student_name = st.text_input("Nome do discente", "João David Monteiro Costa")
    title = st.text_area(
        "Título do trabalho",
        "Influência do tamanho do estímulo e da duração do ciclo no julgamento de uniformidade da velocidade angular de movimentos elípticos",
        height=92,
    )
    advisor_name = st.text_input("Nome do orientador", "Givago da Silva Souza")
    advisor_title = st.selectbox("Título do orientador", ["Prof. Dr.", "Profa. Dra.", "Prof.", "Profa."], index=0)

with right:
    st.subheader("Data, horário e local")
    defense_date = st.date_input("Data", value=date(2026, 7, 9), format="DD/MM/YYYY")
    defense_time = st.time_input("Horário", value=time(18, 30), step=300)
    location = st.text_input("Local/sala/link", "Sala Virtual https://meet.google.com/dec-tnmf-rnv")


st.subheader("Presidência")
president_name = st.text_input("Presidente da banca", advisor_name)
president_title = st.selectbox("Título do presidente", ["Prof. Dr.", "Profa. Dra.", "Prof.", "Profa."], index=0)
president_institution = st.text_input("Instituição do presidente", "UFPA")

st.divider()

st.subheader("Membros titulares")
st.write("Adicione, remova ou edite avaliadores. Cada membro titular gerará uma ficha de avaliação.")
exam_df = st.data_editor(
    st.session_state.get("exam_df", default_examiners()),
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Nome": st.column_config.TextColumn(required=True),
        "Título": st.column_config.SelectboxColumn(options=["Prof. Dr.", "Profa. Dra.", "Prof.", "Profa.", "Dr.", "Dra."]),
        "Instituição": st.column_config.TextColumn(default="UFPA"),
        "Função": st.column_config.SelectboxColumn(options=["membro titular", "membro suplente", "convidado"]),
    },
)
st.session_state.exam_df = exam_df

with st.expander("Membro suplente na ata", expanded=False):
    include_substitute = st.checkbox("Incluir suplente", value=True)
    sub_cols = st.columns([1, 0.35, 0.35])
    with sub_cols[0]:
        substitute_name = st.text_input("Nome do suplente", "Letícima Miquilini de Arruda Farias")
    with sub_cols[1]:
        substitute_title = st.selectbox("Título do suplente", ["Profa. Dra.", "Prof. Dr.", "Dra.", "Dr."], index=0)
    with sub_cols[2]:
        substitute_institution = st.text_input("Instituição do suplente", "UFPA")

with st.expander("Preencher avaliações nas fichas", expanded=False):
    st.write("Se deixar em branco, a ficha sai como formulário para marcação posterior.")
    eval_state = {}
    comments = {}
    for _, row in exam_df.fillna("").iterrows():
        name = str(row.get("Nome", "")).strip()
        if not name:
            continue
        st.markdown(f"**{name}**")
        cols = st.columns(4)
        eval_state[name] = {}
        for idx, item in enumerate(EVAL_ITEMS):
            with cols[idx]:
                eval_state[name][item] = st.selectbox(
                    item,
                    ["em_branco", "adequado", "inadequado"],
                    key=f"eval_{name}_{idx}",
                )
        comments[name] = st.text_area("Observações/comentários", key=f"comments_{name}", height=80)


def build_data() -> DefenseData:
    examiners = []
    for _, row in exam_df.fillna("").iterrows():
        name = str(row.get("Nome", "")).strip()
        if not name:
            continue
        examiners.append(
            Examiner(
                name=name,
                title=str(row.get("Título", "Prof. Dr.")).strip() or "Prof. Dr.",
                institution=str(row.get("Instituição", "UFPA")).strip() or "UFPA",
                role=str(row.get("Função", "membro titular")).strip() or "membro titular",
                evaluation=eval_state.get(name, {}),
                comments=comments.get(name, ""),
            )
        )
    substitutes = []
    if include_substitute and substitute_name.strip():
        substitutes.append(
            Examiner(
                name=substitute_name,
                title=substitute_title,
                institution=substitute_institution or "UFPA",
                role="membro suplente",
            )
        )
    return DefenseData(
        student_name=student_name,
        advisor_name=advisor_name,
        advisor_title=advisor_title,
        title=title,
        defense_date=defense_date,
        defense_time=defense_time,
        location=location,
        program=program,
        institute=institute,
        university=university,
        course_level=course_level,
        document_kind=document_kind,
        work_kind=work_kind,
        student_gender=student_gender,
        president=Examiner(president_name, president_title, president_institution, "Presidente"),
        examiners=examiners,
        substitutes=substitutes,
        decision=decision,
    )


st.divider()
st.subheader("Gerar documentos")

data = build_data()
can_generate = bool(data.student_name.strip() and data.title.strip() and data.advisor_name.strip() and data.examiners)
if not can_generate:
    st.warning("Preencha discente, título, orientador e pelo menos um avaliador.")
else:
    zip_bytes = generate_zip(data)
    ata_bytes = generate_ata_pdf(data)
    st.download_button(
        "Baixar todos os documentos (.zip)",
        data=zip_bytes,
        file_name="documentos_banca.zip",
        mime="application/zip",
        use_container_width=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Baixar ata (.pdf)",
            data=ata_bytes,
            file_name="ata.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with c2:
        if data.examiners:
            first = data.examiners[0]
            st.download_button(
                "Baixar primeira ficha (.pdf)",
                data=generate_ficha_pdf(data, first),
                file_name="ficha_avaliador_1.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

st.info("Dica: mantenha o resultado da ata como 'em_branco' se quiser assinalar APROVAR/REPROVAR manualmente após a banca.")
