# Gerador de ata e fichas de avaliação

Aplicação Streamlit para gerar documentos em PDF a partir dos dados de uma banca do PPGNBC:

- Ata da comissão examinadora
- Fichas de avaliação individuais para cada membro titular
- Arquivo `.zip` com todos os PDFs

## Como executar

No terminal, dentro desta pasta:

```powershell
streamlit run streamlit_app.py
```

Se estiver usando o Python do ambiente do Codex:

```powershell
& "C:\Users\givag\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m streamlit run streamlit_app.py
```

## Campos principais

- Tipo de banca: Qualificação ou Defesa
- Nível: Mestrado ou Doutorado
- Discente, título do trabalho, orientador, data, horário e local
- Presidente da banca
- Membros titulares, usados para gerar as fichas
- Membro suplente, incluído na ata
- Resultado da ata: em branco, aprovado ou reprovado
- Avaliação por item, opcional, para deixar as fichas já preenchidas

## Teste rápido

Para gerar um arquivo ZIP de exemplo sem abrir o Streamlit:

```powershell
& "C:\Users\givag\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" smoke_generate.py
```

O arquivo será salvo em `outputs/documentos_banca_exemplo.zip`.
