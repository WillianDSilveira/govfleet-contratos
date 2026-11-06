import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="GovFleet - Gestão de Contratos e Frota",
    page_icon="🚘",
    layout="wide"
)

# Estilização CSS leve
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# Função para carregar e tratar os dados da planilha
@st.cache_data
def carregar_dados(caminho_arquivo):
    df = pd.read_excel(caminho_arquivo)
    
    # Tratamento dos nomes das Secretarias (Remove pontos e sub-órgãos para consolidação)
    df['Secretaria_Limpa'] = df['Secretaria/Órgão'].apply(
        lambda x: str(x).strip().lstrip('.').split('/')[0].strip()
    )
    
    # Garantir formato de data e moeda
    df['Início Contrato'] = pd.to_datetime(df['Início Contrato'])
    df['Fim Contrato'] = pd.to_datetime(df['Fim Contrato'])
    df['Valor Mensal'] = pd.to_numeric(df['Valor Mensal'], errors='coerce')
    
    return df

# Título Principal
st.title("🚘 GovFleet — Sistema de Controle de Contratos e Frota")
st.caption("Protótipo operacional alimentado automaticamente pela planilha de contratos vigentes.")

# Carregamento do arquivo
caminho_excel = 'Contratos vigentes em 31-10-2026.xlsx'

try:
    df = carregar_dados(caminho_excel)
except Exception as e:
    st.error(f"Erro ao carregar o arquivo {caminho_excel}. Certifique-se de que ele está na mesma pasta do código.")
    st.stop()

# --- BARRA LATERAL (FILTROS DE BUSCA E NAVEGAÇÃO) ---
st.sidebar.header("🔍 Filtros Globais")

# Filtro de Secretaria
secretarias = ["Todas"] + sorted(list(df['Secretaria_Limpa'].unique()))
sec_selecionada = st.sidebar.selectbox("Filtrar por Secretaria", secretarias)

# Filtro de Locadora
locadoras = ["Todas"] + sorted(list(df['Locadora'].unique()))
loc_selecionada = st.sidebar.selectbox("Filtrar por Locadora", locadoras)

# Filtro de Tipo de Veículo
tipos_veiculo = ["Todos"] + sorted(list(df['Tipo Veículo'].unique()))
tipo_selecionado = st.sidebar.selectbox("Filtrar por Tipo de Veículo", tipos_veiculo)

# Aplicando os Filtros
df_filtrado = df.copy()

if sec_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['Secretaria_Limpa'] == sec_selecionada]
if loc_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['Locadora'] == loc_selecionada]
if tipo_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Tipo Veículo'] == tipo_selecionado]

# --- PAINEL DE MÉTRICAS (KPIS) ---
col1, col2, col3, col4 = st.columns(4)

total_valor = df_filtrado['Valor Mensal'].sum()
total_contratos = len(df_filtrado)
ticket_medio = df_filtrado['Valor Mensal'].mean() if total_contratos > 0 else 0
total_secretarias = df_filtrado['Secretaria_Limpa'].nunique()

col1.metric("Valor Mensal Total", f"R$ {total_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
col2.metric("Total de Contratos/Veículos", f"{total_contratos}")
col3.metric("Valor Médio por Veículo", f"R$ {ticket_medio:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
col4.metric("Secretarias Atendidas", f"{total_secretarias}")

st.markdown("---")

# --- GRÁFICOS INTERATIVOS ---
st.subheader("📊 Análise Financeira e Operacional")

tab_graf1, tab_graf2 = st.tabs(["Custo por Secretaria", "Distribuição por Locadora"])

with tab_graf1:
    resumo_sec = df_filtrado.groupby('Secretaria_Limpa')['Valor Mensal'].sum().reset_index()
    resumo_sec = resumo_sec.sort_values(by='Valor Mensal', ascending=False)
    
    fig_sec = px.bar(
        resumo_sec,
        x='Secretaria_Limpa',
        y='Valor Mensal',
        title="Gasto Mensal Total por Secretaria (R$)",
        labels={'Secretaria_Limpa': 'Secretaria', 'Valor Mensal': 'Valor Mensal (R$)'},
        text_auto='.2f',
        color='Valor Mensal',
        color_continuous_scale='Blues'
    )
    fig_sec.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_sec, use_container_width=True)

with tab_graf2:
    resumo_loc = df_filtrado.groupby('Locadora')['Valor Mensal'].agg(['sum', 'count']).reset_index()
    resumo_loc.columns = ['Locadora', 'Valor_Total', 'Quantidade']
    
    fig_loc = px.pie(
        resumo_loc,
        names='Locadora',
        values='Valor_Total',
        title="Market Share por Locadora (Valor Mensal acumulado)",
        hole=0.4
    )
    st.plotly_chart(fig_loc, use_container_width=True)

st.markdown("---")

# --- TABELA DETALHADA E CONSULTA ---
st.subheader("📄 Tabela Geral de Contratos e Frota")

# Barra de pesquisa por texto livre
busca = st.text_input("🔎 Pesquisar por Placa, Número de Contrato ou Edital de Licitação:")

if busca:
    df_filtrado = df_filtrado[
        df_filtrado['Contrato'].astype(str).str.contains(busca, case=False, na=False) |
        df_filtrado['Véiculo Placas'].astype(str).str.contains(busca, case=False, na=False) |
        df_filtrado['Licitação'].astype(str).str.contains(busca, case=False, na=False) |
        df_filtrado['Secretaria/Órgão'].astype(str).str.contains(busca, case=False, na=False)
    ]

# Formatação visual da tabela
df_exibicao = df_filtrado[[
    'Contrato', 'Licitação', 'Secretaria_Limpa', 'Secretaria/Órgão', 
    'Véiculo Placas', 'Tipo Veículo', 'Valor Mensal', 'Início Contrato', 'Fim Contrato', 'Locadora'
]].copy()

df_exibicao['Início Contrato'] = df_exibicao['Início Contrato'].dt.strftime('%d/%m/%Y')
df_exibicao['Fim Contrato'] = df_exibicao['Fim Contrato'].dt.strftime('%d/%m/%Y')
df_exibicao['Valor Mensal'] = df_exibicao['Valor Mensal'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

st.dataframe(df_exibicao, use_container_width=True, height=400)

# Botão de exportação de dados filtrados
st.download_button(
    label="📥 Exportar Relatório Filtrado (CSV)",
    data=df_filtrado.to_csv(index=False).encode('utf-8-sig'),
    file_name="relatorio_contratos_filtrado.csv",
    mime="text/csv"
)