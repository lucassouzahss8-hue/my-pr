import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import urllib.parse

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

# --- CONEXÃO BANCO DE DADOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- INICIALIZAÇÃO DO ESTADO ---
if "n_itens" not in st.session_state:
    st.session_state.n_itens = 1
if "carrinho_orc" not in st.session_state:
    st.session_state.carrinho_orc = []

# --- FUNÇÕES DE DADOS ---
def carregar_ingredientes():
    try:
        df = conn.read(worksheet="Ingredientes", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['nome', 'unidade', 'preco'])
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame(columns=['nome', 'unidade', 'preco'])

def carregar_receitas_nuvem():
    try:
        df = conn.read(worksheet="Receitas", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])
        return df
    except Exception:
        return pd.DataFrame(columns=['nome_receita', 'ingrediente', 'qtd', 'unid'])

def carregar_historico_orc():
    try:
        df = conn.read(worksheet="Orcamentos_Salvos", ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame(columns=['Data', 'Cliente', 'Pedido', 'Valor_Final'])

# --- APP PRINCIPAL ---
def main():
    df_ing = carregar_ingredientes()
    df_rec = carregar_receitas_nuvem()

    st.markdown("<h1 class='titulo-planilha'>📊 Precificador</h1>", unsafe_allow_html=True)

    # --- SIDEBAR: AJUSTE DE TAXAS ---
    with st.sidebar:
        st.header("⚙️ Ajuste de Taxas")
        taxa_credito_input = st.number_input("Taxa Crédito (%)", value=4.99, step=0.01)
        st.divider()
        km_gratis = st.number_input("KM Isentos", value=5)
        valor_por_km = st.number_input("R$ por KM adicional", value=2.0, step=0.1)

    # --- GERENCIAR RECEITAS ---
    with st.expander("📂 Abrir ou Deletar Receitas Salvas"):
        receitas_nomes = df_rec['nome_receita'].unique().tolist() if not df_rec.empty else []
        col_rec1, col_rec2 = st.columns([3, 1])
        with col_rec1:
            receita_selecionada = st.selectbox("Selecione uma receita:", [""] + receitas_nomes)
        with col_rec2:
            st.write("") 
            if st.button("🔄 Carregar", use_container_width=True) and receita_selecionada != "":
                dados_rec = df_rec[df_rec['nome_receita'] == receita_selecionada]
                st.session_state.n_itens = len(dados_rec)
                for idx, row in enumerate(dados_rec.itertuples()):
                    st.session_state[f"nome_{idx}"] = row.ingrediente
                    st.session_state[f"qtd_{idx}"] = float(row.qtd)
                    st.session_state[f"u_{idx}"] = row.unid
                st.rerun()

    # --- CONFIGURAÇÕES DO PRODUTO ---
    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 1, 1, 1])
    with col_p1:
        nome_produto_final = st.text_input("Nome do Produto Final:", key="nome_p_final")
    with col_p2:
        margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0, value=135)
    with col_p3:
        distancia_km = st.number_input("Distância (km)", min_value=0.0, value=0.0, step=0.1)
    with col_p4:
        forma_pagamento = st.selectbox("Pagamento", ["Crédito", "PIX"])
        
    st.divider()

    if df_ing.empty:
        st.warning("⚠️ Adicione ingredientes na aba 'Ingredientes' da sua planilha.")
        return

    # --- ÁREA DOS INGREDIENTES ---
    col_esq, col_dir = st.columns([2, 1])
    with col_esq:
        st.subheader("🛒 Ingredientes")
        n_itens_input = st.number_input("Número de itens:", min_value=1, value=st.session_state.n_itens)
        custo_ingredientes_total = 0.0
        for i in range(int(n_itens_input)):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1.5])
            with c1:
                lista_nomes = df_ing['nome'].tolist()
                escolha = st.selectbox(f"Item {i+1}", options=lista_nomes, key=f"n_sel_{i}")
            dados_item = df_ing[df_ing['nome'] == escolha].iloc[0]
            with c2:
                qtd_usada = st.number_input(f"Qtd", key=f"q_sel_{i}", step=0.01)
            with c3:
                unid_uso = st.selectbox(f"Unid", ["g", "kg", "ml", "L", "unidade"], key=f"u_sel_{i}")

            fator = 1.0
            u_base = str(dados_item['unidade']).lower().strip()
            if unid_uso == "g" and u_base == "kg": fator = 1/1000
            elif unid_uso == "kg" and u_base == "g": fator = 1000
            elif unid_uso == "ml" and u_base == "l": fator = 1/1000
            
            custo_parcial = (qtd_usada * fator) * float(dados_item['preco'])
            custo_ingredientes_total += custo_parcial
            with c4:
                st.markdown(f"<p style='padding-top:35px; font-weight:bold;'>R$ {custo_parcial:.2f}</p>", unsafe_allow_html=True)

    with col_dir:
        st.subheader("⚙️ Adicionais")
        perc_quebra = st.slider("Quebra (%)", 0, 15, 2)
        perc_despesas = st.slider("Despesas Gerais (%)", 0, 100, 30)
        valor_embalagem_manual = st.number_input("Embalagem (R$)", min_value=0.0, value=0.0)

    # --- CÁLCULOS TELA DE PRECIFICAÇÃO ---
    v_quebra = custo_ingredientes_total * (perc_quebra / 100)
    v_despesas = custo_ingredientes_total * (perc_despesas / 100)
    v_cmv = custo_ingredientes_total + v_quebra + valor_embalagem_manual
    custo_total_prod = v_cmv + v_despesas
    lucro_valor = custo_total_prod * (margem_lucro / 100)
    preco_venda_base = custo_total_prod + lucro_valor
    taxa_entrega = (distancia_km - km_gratis) * valor_por_km if distancia_km > km_gratis else 0.0
    v_taxa_financeira = (preco_venda_base + taxa_entrega) * (taxa_credito_input/100) if forma_pagamento == "Crédito" else 0.0
    preco_venda_final = preco_venda_base + taxa_entrega + v_taxa_financeira

    # Detalhamento Visual (MANTIDO)
    st.divider()
    res1, res2 = st.columns([1.5, 1])
    with res1:
        df_resumo = pd.DataFrame({
            "Item": ["Ingredientes", "Quebra", "Despesas", "Embalagem", "Custo Produção", "Lucro", "Entrega", "Taxas", "TOTAL"],
            "Valor": [f"R$ {custo_ingredientes_total:.2f}", f"R$ {v_quebra:.2f}", f"R$ {v_despesas:.2f}", f"R$ {valor_embalagem_manual:.2f}", f"R$ {custo_total_prod:.2f}", f"R$ {lucro_valor:.2f}", f"R$ {taxa_entrega:.2f}", f"R$ {v_taxa_financeira:.2f}", f"R$ {preco_venda_final:.2f}"]
        })
        st.table(df_resumo)

    with res2:
        st.markdown(f"<div class='resultado-box'><h2>TOTAL ({forma_pagamento})</h2><h1>R$ {preco_venda_final:.2f}</h1><p>Custo Produção: R$ {custo_total_prod:.2f}</p></div>", unsafe_allow_html=True)

    # =========================================================
    # --- SEÇÃO DE ORÇAMENTO (AJUSTE SOLICITADO) ---
    # =========================================================
    st.divider()
    st.markdown("<h2 class='titulo-planilha'>📋 Gerador de Orçamentos</h2>", unsafe_allow_html=True)
    
    col_o1, col_o2 = st.columns([3, 1])
    it_orc = col_o1.selectbox("Escolha o Item:", options=[""] + df_ing['nome'].tolist(), key="it_o")
    q_orc = col_o2.number_input("Qtd:", min_value=1, value=1, key="q_o")
    
    if st.button("➕ Adicionar"):
        if it_orc:
            p_puro = float(df_ing[df_ing['nome'] == it_orc]['preco'].iloc[0])
            st.session_state.carrinho_orc.append({"nome": it_orc, "qtd": q_orc, "preco_puro": p_puro})
            st.rerun()

    if st.session_state.carrinho_orc:
        total_venda_acum = 0.0
        cols_h = st.columns([3, 1, 1.5, 1.5, 2, 0.5])
        cols_h[0].write("**Produto**")
        cols_h[1].write("**Qtd**")
        cols_h[2].write("**Unit. Puro**")
        cols_h[3].write("**Unit. Custo**")
        cols_h[4].write("**Subtotal Venda**")

        for idx, item in enumerate(st.session_state.carrinho_orc):
            c = st.columns([3, 1, 1.5, 1.5, 2, 0.5])
            
            # --- LÓGICA ALTERADA CONFORME SOLICITADO ---
            # Unitário Custo = Apenas Unitário Puro * Quantidade (sem taxas extras aqui)
            unit_custo_exibicao = item['preco_puro'] * item['qtd']
            
            # Para o cálculo de venda, mantemos o conceito de Custo Real + Margem (como no precificador)
            c_real_unit = item['preco_puro'] + (item['preco_puro'] * (perc_quebra/100)) + (item['preco_puro'] * (perc_despesas/100))
            venda_subtotal = (c_real_unit * (1 + (margem_lucro/100))) * item['qtd']
            total_venda_acum += venda_subtotal
            
            c[0].write(item['nome'])
            c[1].write(f"{item['qtd']}")
            c[2].write(f"R$ {item['preco_puro']:.2f}")
            c[3].write(f"R$ {unit_custo_exibicao:.2f}") # Exibe apenas Puro * Qtd
            c[4].write(f"**R$ {venda_subtotal:.2f}**")
            if c[5].button("❌", key=f"del_{idx}"):
                st.session_state.carrinho_orc.pop(idx)
                st.rerun()

        st.divider()
        col_ad1, col_ad2 = st.columns(2)
        frete_f = col_ad1.number_input("Frete (R$)", value=0.0)
        emb_f = col_ad2.number_input("Embalagem (R$)", value=0.0)
        
        venda_com_taxas = total_venda_acum + frete_f + emb_f
        taxa_cartao = venda_com_taxas * (taxa_credito_input/100) if forma_pagamento == "Crédito" else 0.0
        total_geral = venda_com_taxas + taxa_cartao
        
        st.markdown(f"## TOTAL FINAL: R$ {total_geral:.2f}")
        if st.button("🗑️ Limpar"):
            st.session_state.carrinho_orc = []
            st.rerun()

if __name__ == "__main__":
    main()
