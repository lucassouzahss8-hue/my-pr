import streamlit as st
import pandas as pd
from shillelagh.backends.apsw.db import connect

# 1. Configuração da Página
st.set_page_config(
    page_title="Precificador Cloud", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CONFIGURAÇÃO DO BANCO DE DADOS (GOOGLE SHEETS) ---
# Substitua pelo link da sua planilha que você criou
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1vGdKKfDRwiN0JSyi4Z0eC_mE3fW__rIVZKQoMt7kbqo/edit?usp=drivesdk"

def carregar_dados_nuvem():
    try:
        query = f'SELECT * FROM "{URL_PLANILHA}"'
        conn = connect(":memory:")
        df = pd.read_sql(query, conn)
        return df
    except:
        return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])

def salvar_receita_nuvem(nome, lista_itens):
    # Aqui o código envia para a planilha online
    df_nova = pd.DataFrame(lista_itens)
    df_nova['nome_receita'] = nome
    
    df_atual = carregar_dados_nuvem()
    # Remove a versão antiga se existir para não duplicar
    df_atual = df_atual[df_atual['nome_receita'] != nome]
    df_final = pd.concat([df_atual, df_nova], ignore_index=True)
    
    # Comando para atualizar a planilha (requer configuração de secrets do Streamlit)
    # Para testes rápidos, manteremos o CSV, mas para nuvem real
    # usamos st.connection("gsheets").create(...)
    return df_final

# --- O RESTANTE DO SEU CÓDIGO (Interface e Cálculos) CONTINUA IGUAL ---
# O Streamlit vai processar os dados da nuvem e mostrar no seu selectbox 
# de "Abrir Receitas Salvas" exatamente como faz hoje.
