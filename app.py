import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from streamlit_calendar import calendar
import os
import pytz

# ========== STREAMLIT CONFIG ==========
from notion_client import Client
st.set_page_config(page_title="Controle Financeiro", layout="centered")

# ========== CSS INSPIRADO NO BANCO XP ==========
css = """
<style>
body {
    background-color: #111217;
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
}
[data-testid="stSidebar"] {
    background-color: #0e0f12;
}
h1, h2, h3, h4 {
    color: #ffffff;
    font-weight: 600;
}
div[data-testid="metric-container"] {
    background-color: #1a1c21;
    padding: 1rem;
    border-radius: 10px;
    box-shadow: 0 0 5px rgba(0,0,0,0.3);
    margin-bottom: 1rem;
}
div[data-testid="metric-container"] label {
    color: #aaa;
}
.stButton > button {
    background-color: #04AA6D;
    color: white;
    border: none;
    padding: 0.5rem 1.2rem;
    border-radius: 8px;
    font-weight: bold;
    transition: all 0.3s ease;
}
.stButton > button:hover {
    background-color: #038857;
    transform: scale(1.05);
}
.stCheckbox > div {
    color: #ccc;
}
.stTextInput > div > div > input,
.stDateInput input,
.stTimeInput input,
.stSelectbox select {
    background-color: #1f2125;
    color: white;
    border: 1px solid #333;
    border-radius: 5px;
}
.aba-btn {
    width: 100%;
    padding: 0.75rem;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    margin-bottom: 0.5rem;
    background-color: #1a1c21;
    color: #ffffff;
    transition: all 0.3s ease;
    box-shadow: 0 0 8px rgba(0,0,0,0.2);
    cursor: pointer;
}
.aba-btn:hover {
    background-color: #2a2d33;
    transform: scale(1.05);
    box-shadow: 0 0 12px rgba(0,0,0,0.4);
}
.aba-btn.ativo {
    background-color: #04AA6D;
    color: white;
    box-shadow: 0 0 12px rgba(4, 170, 109, 0.6);
}
.stTextInput > div > div > input:focus,
.stDateInput input:focus,
.stTimeInput input:focus,
.stSelectbox select:focus {
    border: 1px solid #04AA6D;
    box-shadow: 0 0 6px #04AA6D66;
    outline: none;
}
.st-expanderHeader {
    background-color: #1a1c21;
    color: #04AA6D;
    font-weight: bold;
    border-radius: 8px;
}
.st-expanderContent {
    background-color: #181a1e;
    padding: 1rem;
    border-radius: 0 0 8px 8px;
    border-top: 1px solid #333;
}
.stMetric {
    background-color: #1a1c21;
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1rem;
    text-align: center;
}
.stMetric > div {
    color: #ffffff;
    font-size: 1.2rem;
    font-weight: bold;
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ========== GOOGLE SHEETS ==========
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
client = gspread.authorize(creds)
sheet = client.open("OrganizacaoFinanceira").sheet1
resumo_sheet = client.open("OrganizacaoFinanceira").worksheet("Resumo")

# ========== GOOGLE CALENDAR ==========
def criar_evento_no_calendario(descricao, valor, data, tipo):
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    if os.path.exists('token_calendar.json'):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file('token_calendar.json', SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials_calendar.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token_calendar.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    inicio = datetime.strptime(data, '%d/%m/%Y').replace(hour=10, minute=0)
    fim = inicio + timedelta(hours=1)
    evento = {
        'summary': f'{tipo}: {descricao}',
        'description': f'Valor: R$ {valor}',
        'start': {'dateTime': inicio.isoformat(), 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': fim.isoformat(), 'timeZone': 'America/Sao_Paulo'},
    }
    evento_criado = service.events().insert(calendarId='primary', body=evento).execute()
    return evento_criado.get('htmlLink')

# ========== NOTION CONFIG ==========
NOTION_TOKEN = "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"
NOTION_PAGE_ID = "214d9b59-0417-8061-b71d-e862735c048e"
notion = Client(auth=NOTION_TOKEN)

def atualizar_pagina_notion(pagina_id, conteudo):
    try:
        notion.blocks.children.append(
            pagina_id,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": conteudo}
                            }
                        ]
                    }
                }
            ]
        )
    except Exception as e:
        st.error(f"Erro ao atualizar nota: {e}")

def listar_paginas_notion():
    try:
        resultados = notion.search(query="", filter={"property": "object", "value": "page"})
        paginas = []
        for resultado in resultados.get("results", []):
            props = resultado.get("properties", {})
            titulo = "Sem título"
            for val in props.values():
                if val.get("type") == "title" and val.get("title"):
                    titulo = val["title"][0].get("text", {}).get("content", "Sem título")
                    break
            paginas.append((titulo, resultado["id"]))
        return paginas
    except Exception as e:
        st.error(f"Erro ao buscar páginas no Notion: {e}")
        return []

# ========== STREAMLIT INTERFACE ==========
st.title("💸 Controle Financeiro")

if 'aba' not in st.session_state:
    st.session_state['aba'] = "Adicionar"

with st.sidebar:
    st.markdown("## Navegação")
    if st.button("➕ Adicionar"):
        st.session_state['aba'] = "Adicionar"
    if st.button("📊 Saldo"):
        st.session_state['aba'] = "Saldo"
    if st.button("📆 Calendário"):
        st.session_state['aba'] = "Calendário"
    if st.button("📝 Notas"):
        st.session_state['aba'] = "Notas"

aba = st.session_state['aba']

if aba == "Adicionar":
    st.subheader("➕ Nova transação")
    tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
    descricao = st.text_input("Descrição")
    valor = st.text_input("Valor (R$)")
    data = st.date_input("Data", value=datetime.today())
    data_formatada = data.strftime('%d/%m/%Y')
    adicionar_ao_calendario = st.checkbox("Adicionar ao Google Calendar")

    if st.button("💾 Salvar"):
        if descricao and valor:
            sheet.append_row([tipo, descricao, valor, data_formatada])
            if adicionar_ao_calendario:
                link = criar_evento_no_calendario(descricao, valor, data_formatada, tipo)
                st.success("Transação e evento criados!")
                st.markdown(f"[Ver no Google Calendar]({link})")
            else:
                st.success("Transação salva com sucesso!")
        else:
            st.warning("Preencha todos os campos.")

elif aba == "Saldo":
    st.markdown("""
### 📊 Visão Geral das Finanças
Acompanhe aqui suas receitas, despesas e o saldo total do período registrado:
""")
    registros = sheet.get_all_values()[1:]
    total_receitas, total_despesas = 0, 0
    dados_movimentacoes = []
    for linha in registros:
        if len(linha) < 3:
            continue
        tipo, descricao, valor_str = linha[:3]
        try:
            valor = float(valor_str.replace(',', '.'))
            if tipo.lower() == 'receita':
                total_receitas += valor
            elif tipo.lower() == 'despesa':
                total_despesas += valor
            dados_movimentacoes.append({"tipo": tipo, "descricao": descricao, "valor": valor})
        except:
            continue
    saldo = total_receitas - total_despesas
    resumo_sheet.update('A1', [['Resumo']])
    resumo_sheet.update('A2', [['Receitas']])
    resumo_sheet.update('B2', [[f"{total_receitas:.2f}"]])
    resumo_sheet.update('A3', [['Despesas']])
    resumo_sheet.update('B3', [[f"{total_despesas:.2f}"]])
    resumo_sheet.update('A4', [['Saldo']])
    resumo_sheet.update('B4', [[f"{saldo:.2f}"]])
    col1, col2, col3 = st.columns(3)
    col1.metric("Receitas", f"R$ {total_receitas:.2f}")
    col2.metric("Despesas", f"R$ {total_despesas:.2f}")
    col3.metric("Saldo", f"R$ {saldo:.2f}")

    st.markdown("""
---
### 📋 Detalhamento das Movimentações
Veja abaixo todas as entradas e saídas já registradas:
""")
    for i, mov in enumerate(dados_movimentacoes):
        st.write(f"{i+1}. {mov['tipo']} - {mov['descricao']} - R$ {mov['valor']:.2f}")
        if st.button(f"Excluir {i+1}"):
            sheet.delete_rows(i+2)
            st.rerun()

elif aba == "Calendário":
    st.markdown("""
### 📆 Planejamento Financeiro
Visualize aqui suas movimentações organizadas por data no calendário interativo:
""")
    registros = sheet.get_all_values()[1:]
    eventos = []
    for linha in registros:
        if len(linha) < 4:
            continue
        tipo, desc, valor, data_str = linha[:4]
        try:
            data_obj = datetime.strptime(data_str, "%d/%m/%Y")
        except:
            continue
        eventos.append({
            "title": f"{tipo}: {desc} (R${valor})",
            "start": data_obj.strftime("%Y-%m-%dT10:00:00"),
            "end": data_obj.strftime("%Y-%m-%dT11:00:00")
        })
    calendar(events=eventos, options={"initialView": "dayGridMonth", "locale": "pt-br"})

elif aba == "Notas":
    st.markdown("""
### 📝 Suas Anotações no Notion
Crie ou edite anotações pessoais diretamente integradas com seu Notion:
""")
    modo = st.radio("Modo", ["Criar nova página", "Editar nota existente"])

    if modo == "Criar nova página":
        titulo = st.text_input("Título")
        conteudo = st.text_area("Conteúdo")
        if st.button("📥 Criar página"):
            if conteudo:
                try:
                    notion.pages.create(
                        parent={"page_id": NOTION_PAGE_ID},
                        properties={
                            "title": {
                                "title": [
                                    {"type": "text", "text": {"content": titulo or "Sem título"}}
                                ]
                            }
                        },
                        children=[
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {"type": "text", "text": {"content": conteudo}}
                                    ]
                                }
                            }
                        ]
                    )
                    st.success("Página criada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao criar nota: {e}")
            else:
                st.warning("Digite algum conteúdo para salvar.")

    elif modo == "Editar nota existente":
        paginas = listar_paginas_notion()
        if paginas:
            opcoes = {titulo: pid for titulo, pid in paginas}
            nota_escolhida = st.selectbox("Escolha a nota", options=list(opcoes.keys()))
            conteudo = st.text_area("Conteúdo a adicionar")
            if st.button("📝 Adicionar conteúdo"):
                if conteudo:
                    atualizar_pagina_notion(opcoes[nota_escolhida], conteudo)
                    st.success("Nota atualizada com sucesso!")
                else:
                    st.warning("Digite algum conteúdo para adicionar.")
        else:
            st.info("Nenhuma nota encontrada.")
