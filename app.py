import streamlit as st
import pandas as pd
import os
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da Página
st.set_page_config(
    page_title="Precificador", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Estilização CSS
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .titulo-planilha { 
        color: #1e3a8a; 
        font-weight: bold; 
        border-bottom: 2px solid #1e3a8a; 
        margin-bottom: 20px; 
        text-align: center;
    }
    .resultado-box { 
        background-color: #262730; 
        padding: 25px; 
        border-radius: 15px; 
        border-left: 10px solid #1e3a8a; 
        box-shadow: 2px 2px 15px rgba(0,0,0,0.3); 
        color: white; 
    }
    .resultado-box h1, .resultado-box h2, .resultado-box p, .resultado-box b { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO BANCO DE DADOS (GOOGLE SHEETS) ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1vGdKKfDRwiN0JSyi4Z0eC_mE3fW__rIVZKQoMt7kbqo/edit?usp=drivesdk"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SIDEBAR: CONTROLE DE TAXAS ---
with st.sidebar:
    st.header("⚙️ Ajuste de Taxas")
    st.divider()
    taxa_debito_input = st.number_input("Taxa Débito (%)", value=1.99, step=0.01)
    taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99, step=0.01)
    st.divider()
    km_gratis = st.number_input("KM Isentos", value=5)
    valor_por_km = st.number_input("R$ por KM adicional", value=2.0, step=0.1)

# --- INICIALIZAÇÃO DO ESTADO ---
if "n_itens" not in st.session_state:
    st.session_state.n_itens = 1
if "nome_prod" not in st.session_state:
    st.session_state.nome_prod = ""

# --- FUNÇÕES DE DADOS ---
def carregar_ingredientes():
    try:
        df = pd.read_csv("ingredientes.csv")
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

def carregar_receitas_nuvem():
    try:
        return conn.read(spreadsheet=URL_PLANILHA)
    except:
        return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])

# --- APP PRINCIPAL ---
def main():
    df_ing = carregar_ingredientes()
    df_rec = carregar_receitas_nuvem()

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador</h1>", unsafe_allow_html=True)

    # --- GERENCIAR RECEITAS ---
    with st.expander("📂 Abrir ou Deletar Receitas Salvas"):
        receitas_nomes = df_rec['nome_receita'].unique().tolist() if not df_rec.empty else []
        col_rec1, col_rec2 = st.columns([3, 1])
        with col_rec1:
            receita_selecionada = st.selectbox("Selecione uma receita:", [""] + receitas_nomes)
        with col_rec2:
            st.write("") 
            st.write("") 
            if st.button("🔄 Carregar", use_container_width=True):
                if receita_selecionada != "":
                    dados_rec = df_rec[df_rec['nome_receita'] == receita_selecionada]
                    st.session_state.nome_prod = receita_selecionada
                    st.session_state.n_itens = len(dados_rec)
                    for idx, row in enumerate(dados_rec.itertuples()):
                        st.session_state[f"nome_{idx}"] = row.ingrediente
                        st.session_state[f"qtd_{idx}"] = float(row.qtd)
                        st.session_state[f"u_{idx}"] = row.unid
                    st.rerun()
            if st.button("🗑️ Deletar", use_container_width=True):
                if receita_selecionada != "":
                    df_final = df_rec[df_rec['nome_receita'] != receita_selecionada]
                    conn.update(spreadsheet=URL_PLANILHA, data=df_final)
                    st.rerun()

    # --- CONFIGURAÇÕES DO PRODUTO ---
    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
    with col_p1:
        nome_produto_final = st.text_input("Nome do Produto Final:", key="nome_prod", placeholder="Ex: Bolo de Pote")
    with col_p2:
        margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0, value=150)
    with col_p3:
        distancia_km = st.number_input("Distância (km)", min_value=0.0, value=None, step=0.1, placeholder="Ex: 8.0")
    with col_p4:
        forma_pagamento = st.selectbox("Pagamento", ["PIX", "Débito", "Crédito"])
        
    st.divider()

    if df_ing.empty:
        st.error("⚠️ O arquivo 'ingredientes.csv' não foi detectado.")
        return

    # --- INGREDIENTES ---
    col_esq, col_dir = st.columns([2, 1])
    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens_input = st.number_input("Número de itens:", min_value=1, key="n_itens")
        custo_ingredientes_total = 0.0
        lista_para_salvar = []

        for i in range(int(n_itens_input)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            with c1:
                default_index = 0
                if f"nome_{i}" in st.session_state:
                    try: default_index = df_ing['nome'].tolist().index(st.session_state[f"nome_{i}"])
                    except: pass
                escolha = st.selectbox(f"Item {i+1}", options=df_ing['nome'].tolist(), key=f"nome_{i}", index=default_index)
            
            dados_item = df_ing[df_ing['nome'] == escolha].iloc[0]
            unid_base = str(dados_item['unidade']).lower().strip()
            preco_base = float(dados_item['preco'])

            with c2:
                qtd_usada = st.number_input(f"Qtd", min_value=0.0, key=f"qtd_{i}", step=0.01, value=st.session_state.get(f"qtd_{i}", 0.0))
            with c3:
                unid_uso = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_{i}")

            val_qtd = qtd_usada if qtd_usada is not None else 0.0
            fator = 1.0
            if unid_uso == "g" and unid_base == "kg": fator = 1/1000
            elif unid_uso == "kg" and unid_base == "g": fator = 1000
            elif unid_uso.lower() == "ml" and unid_base.lower() == "l": fator = 1/1000
            elif unid_uso.lower() == "l" and unid_base.lower() == "ml": fator = 1000
            
            custo_parcial = (val_qtd * fator) * preco_base
            custo_ingredientes_total += custo_parcial
            lista_para_salvar.append({"nome_receita": nome_produto_final, "ingrediente": escolha, "qtd": val_qtd, "unid": unid_uso})
            with c4:
                st.markdown(f"<p style='padding-top:35px; font-weight:bold;'>R$ {custo_parcial:.2f}</p>", unsafe_allow_html=True)

    with col_dir:
        st.subheader("⚙️ Adicionais")
        perc_quebra = st.slider("Quebra (%)", 0, 15, 5)
        perc_despesas = st.slider("Despesas Gerais (%)", 0, 100, 30)
        valor_embalagem = st.number_input("Embalagem (R$)", min_value=0.0, value=None, step=0.1, placeholder="0.0")

    # --- CÁLCULOS FINAIS ---
    val_dist = distancia_km if distancia_km is not None else 0.0
    val_emb = valor_embalagem if valor_embalagem is not None else 0.0
    taxa_entrega = (val_dist - km_gratis) * valor_por_km if val_dist > km_gratis else 0.0

    v_quebra = custo_ingredientes_total * (perc_quebra / 100)
    v_despesas = custo_ingredientes_total * (perc_despesas / 100)
    v_cmv_direto = custo_ingredientes_total + v_quebra + val_emb
    
    custo_total_prod = v_cmv_direto + v_despesas
    lucro_valor = custo_total_prod * (margem_lucro / 100)
    preco_venda_produto = custo_total_prod + lucro_valor
    
    perc_cmv = (v_cmv_direto / preco_venda_produto * 100) if preco_venda_produto > 0 else 0.0
    cor_cmv = "#4ade80" if perc_cmv <= 35 else "#facc15" if perc_cmv <= 45 else "#f87171"

    if forma_pagamento == "Débito": t_percentual = taxa_debito_input / 100
    elif forma_pagamento == "Crédito": t_percentual = taxa_credito_input / 100
    else: t_percentual = 0.0
    
    valor_base_taxa = preco_venda_produto + taxa_entrega
    v_taxa_financeira = valor_base_taxa * t_percentual
    preco_venda_final = valor_base_taxa + v_taxa_financeira

    # --- TABELA E QUADRADO DE RESULTADOS ---
    st.divider()
    res1, res2 = st.columns([1.5, 1])
    with res1:
        st.markdown(f"### Detalhamento: {nome_produto_final if nome_produto_final else 'Novo Produto'}")
        df_resumo = pd.DataFrame({
            "Item": ["Ingredientes", "Quebra", "Despesas", "Embalagem", "Custo Produção", "Lucro", f"Entrega ({val_dist}km)", f"Taxa {forma_pagamento}", "TOTAL A COBRAR"],
            "Valor": [f"R$ {custo_ingredientes_total:.2f}", f"R$ {v_quebra:.2f}", f"R$ {v_despesas:.2f}", f"R$ {val_emb:.2f}", f"R$ {custo_total_prod:.2f}", f"R$ {lucro_valor:.2f}", f"R$ {taxa_entrega:.2f}", f"R$ {v_taxa_financeira:.2f}", f"R$ {preco_venda_final:.2f}"]
        })
        st.table(df_resumo)
        
        if st.button("💾 Salvar Receita"):
            if nome_produto_final:
                df_nova = pd.DataFrame(lista_para_salvar)
                df_final = pd.concat([df_rec[df_rec['nome_receita'] != nome_produto_final], df_nova], ignore_index=True)
                conn.update(spreadsheet=URL_PLANILHA, data=df_final)
                st.success(f"Receita '{nome_produto_final}' salva na nuvem!")
                st.rerun()

    with res2:
        st.markdown(f"""
        <div class='resultado-box'>
            <p style='margin:0; font-size:14px; opacity: 0.8;'>{nome_produto_final.upper() if nome_produto_final else 'PRODUTO NOVO'}</p>
            <h2 style='margin:0;'>TOTAL ({forma_pagamento})</h2>
            <h1 style='color: #60a5fa !important; font-size:48px;'>R$ {preco_venda_final:.2f}</h1>
            <hr style='border-color: #4b5563;'>
            <p style='font-size: 22px;'>CMV: <span style='color:{cor_cmv}; font-weight: bold;'>{perc_cmv:.1f}%</span></p>
            <p><b>Preço do Produto:</b> R$ {preco_venda_produto:.2f}</p>
            <p><b>Entrega:</b> R$ {taxa_entrega:.2f}</p>
            <p><b>Seu Lucro Líquido:</b> <span style='color: #4ade80;'>R$ {lucro_valor:.2f}</span></p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
